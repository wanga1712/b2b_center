"""
Сервис формирования данных карточки сделки воронки продаж
для отображения в детальном окне (Поставка материалов и др.).
"""

from typing import Any, Dict, List, Optional

from loguru import logger
from psycopg2.extras import RealDictCursor

from core.tender_database import TenderDatabaseManager
from modules.crm.sales_funnel.models import Deal, PipelineType


class DealDetailService:
    """Сервис агрегации данных для карточки сделки."""

    def __init__(self, db_manager: TenderDatabaseManager):
        self.db_manager = db_manager

    def build_deal_card(self, deal: Deal) -> Dict[str, Any]:
        """
        Формирование агрегированной модели данных для карточки сделки.

        Использует:
        - данные сделки (sales_deals),
        - metadata.original_data (синхронизированные данные закупки),
        - contact/contact_link,
        - deal_item.
        """
        tender_data = self._extract_tender_data_from_metadata(deal)
        customer_id = tender_data.get("customer_id")
        contractor_id = tender_data.get("contractor_id")

        customer = self._load_customer(customer_id) if customer_id else None
        contractor = self._load_contractor(contractor_id) if contractor_id else None

        contacts_customer, contacts_contractor, contacts_deal = self._load_contacts(
            customer_id=customer_id,
            contractor_id=contractor_id,
            deal_id=deal.id,
        )
        deal_items = self._load_deal_items(deal.id) if deal.id else []

        return {
            "deal": self._serialize_deal(deal),
            "tender": tender_data,
            "customer": customer,
            "contractor": contractor,
            "contacts": {
                "customer": contacts_customer,
                "contractor": contacts_contractor,
                "deal": contacts_deal,
            },
            "items": deal_items,
        }

    @staticmethod
    def _extract_tender_data_from_metadata(deal: Deal) -> Dict[str, Any]:
        """
        Извлекает оригинальные данные закупки из metadata сделки.

        Ожидает структуру:
        metadata = {
            "registry_type": "44fz" | "223fz",
            "tender_id": int,
            "original_data": {...}  # результат DealSyncService._get_tender_data
        }
        """
        if not deal.metadata:
            return {}

        original = deal.metadata.get("original_data") or {}
        # Гарантируем наличие базовых полей
        if "registry_type" not in original and deal.metadata.get("registry_type"):
            original["registry_type"] = deal.metadata.get("registry_type")
        if "tender_id" not in original and deal.metadata.get("tender_id"):
            original["tender_id"] = deal.metadata.get("tender_id")

        return original

    def _load_customer(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Загрузка заказчика по ID из таблицы customer."""
        try:
            rows = self.db_manager.execute_query(
                """
                SELECT *
                FROM customer
                WHERE id = %s
                """,
                (customer_id,),
                RealDictCursor,
            )
            return dict(rows[0]) if rows else None
        except Exception as exc:  # pragma: no cover - защита от падения UI
            logger.error(f"Ошибка при загрузке заказчика {customer_id}: {exc}", exc_info=True)
            return None

    def _load_contractor(self, contractor_id: int) -> Optional[Dict[str, Any]]:
        """Загрузка подрядчика по ID из таблицы contractor."""
        try:
            rows = self.db_manager.execute_query(
                """
                SELECT *
                FROM contractor
                WHERE id = %s
                """,
                (contractor_id,),
                RealDictCursor,
            )
            return dict(rows[0]) if rows else None
        except Exception as exc:  # pragma: no cover
            logger.error(f"Ошибка при загрузке подрядчика {contractor_id}: {exc}", exc_info=True)
            return None

    def _load_contacts(
        self,
        customer_id: Optional[int],
        contractor_id: Optional[int],
        deal_id: Optional[int],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Загрузка контактов по заказчику, подрядчику и сделке.

        Возвращает три списка:
        - контакты заказчика,
        - контакты подрядчика,
        - контакты, привязанные непосредственно к сделке.
        """
        try:
            contacts_customer: List[Dict[str, Any]] = []
            contacts_contractor: List[Dict[str, Any]] = []
            contacts_deal: List[Dict[str, Any]] = []

            if customer_id:
                contacts_customer = self._load_contacts_by_filter(customer_id=customer_id)
            if contractor_id:
                contacts_contractor = self._load_contacts_by_filter(contractor_id=contractor_id)
            if deal_id:
                contacts_deal = self._load_contacts_by_filter(deal_id=deal_id)

            return contacts_customer, contacts_contractor, contacts_deal
        except Exception as exc:  # pragma: no cover
            logger.error(f"Ошибка при загрузке контактов: {exc}", exc_info=True)
            return [], [], []

    def _load_contacts_by_filter(
        self,
        customer_id: Optional[int] = None,
        contractor_id: Optional[int] = None,
        deal_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Внутренний хелпер: загрузка контактов по одному из фильтров."""
        where_clauses = []
        params: list[Any] = []

        if customer_id is not None:
            where_clauses.append("cl.customer_id = %s")
            params.append(customer_id)
        if contractor_id is not None:
            where_clauses.append("cl.contractor_id = %s")
            params.append(contractor_id)
        if deal_id is not None:
            where_clauses.append("cl.deal_id = %s")
            params.append(deal_id)

        if not where_clauses:
            return []

        where_sql = " OR ".join(where_clauses)

        rows = self.db_manager.execute_query(
            f"""
            SELECT
                c.id            AS contact_id,
                c.full_name,
                c.department,
                c.position,
                c.phone_mobile,
                c.email,
                c.notes,
                cl.role,
                cl.is_primary,
                cl.customer_id,
                cl.contractor_id,
                cl.deal_id
            FROM contact_link cl
            JOIN contact c ON c.id = cl.contact_id
            WHERE {where_sql}
            ORDER BY c.full_name
            """,
            tuple(params),
            RealDictCursor,
        )
        return [dict(row) for row in rows] if rows else []

    def _load_deal_items(self, deal_id: int) -> List[Dict[str, Any]]:
        """Загрузка позиций КП (deal_item) по сделке."""
        rows = self.db_manager.execute_query(
            """
            SELECT
                id,
                product_name,
                product_code,
                is_analog,
                unit,
                quantity,
                price_per_unit,
                total_price,
                comment
            FROM deal_item
            WHERE deal_id = %s
            ORDER BY id
            """,
            (deal_id,),
            RealDictCursor,
        )
        return [dict(row) for row in rows] if rows else []

    @staticmethod
    def _serialize_deal(deal: Deal) -> Dict[str, Any]:
        """Сериализация объекта Deal в JSON-совместимый словарь."""
        return {
            "id": deal.id,
            "pipeline_type": deal.pipeline_type.value if isinstance(deal.pipeline_type, PipelineType) else str(
                deal.pipeline_type
            ),
            "stage_id": deal.stage_id,
            "tender_id": deal.tender_id,
            "name": deal.name,
            "description": deal.description,
            "amount": deal.amount,
            "margin": deal.margin,
            "status": deal.status.value if hasattr(deal.status, "value") else str(deal.status),
            "tender_status_id": deal.tender_status_id,
            "user_id": deal.user_id,
            "created_at": deal.created_at,
            "updated_at": deal.updated_at,
        }


