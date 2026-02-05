"""
MODULE: modules.crm.sales_funnel.deal_detail_service
RESPONSIBILITY: Service for aggregating deal card data (DAL/Facade).
ALLOWED: typing, loguru, psycopg2, core.tender_database, modules.crm.sales_funnel.models.
FORBIDDEN: UI interaction.
ERRORS: None.

Сервис формирования данных карточки сделки воронки продаж
для отображения в детальном окне (Поставка материалов и др.).
"""

from typing import Any, Dict, List, Optional
from functools import lru_cache

from loguru import logger
from psycopg2.extras import RealDictCursor

from core.tender_database import TenderDatabaseManager
from modules.crm.sales_funnel.models import Deal, PipelineType


class DealDetailService:
    """Сервис агрегации данных для карточки сделки."""

    # Кеш для данных карточек сделок (deal_id -> данные карточки)
    _deal_card_cache: Dict[int, Dict[str, Any]] = {}

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
        
        Данные кешируются для быстрой повторной загрузки карточек.
        """
        # Проверяем кеш
        if deal.id and deal.id in self._deal_card_cache:
            cached_data = self._deal_card_cache[deal.id]
            # Проверяем, не устарели ли данные (сравниваем updated_at)
            cached_deal = cached_data.get("deal", {})
            if cached_deal.get("updated_at") == deal.updated_at:
                logger.debug(f"DealDetailService.build_deal_card: используем кеш для deal_id={deal.id}")
                return cached_data
        
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

        # Сериализуем сделку и обогащаем данными этапа (для отображения в UI)
        deal_dict = self._serialize_deal(deal)
        if deal.stage_id is not None:
            deal_dict["stage_name"] = self._load_stage_name(deal.stage_id)
        else:
            deal_dict["stage_name"] = None

        # Загружаем найденные фразы из tender_document_match_details
        tender_id_for_query = tender_data.get("id") or tender_data.get("tender_id") or deal.tender_id
        registry_type_for_query = deal.metadata.get("registry_type") if deal.metadata else None
        
        # #region agent log
        logger.info(f"DealDetailService.build_deal_card: tender_id={tender_id_for_query}, registry_type={registry_type_for_query}, deal.tender_id={deal.tender_id}")
        # #endregion
        
        found_phrases = self._load_found_phrases(
            tender_id=tender_id_for_query,
            registry_type=registry_type_for_query,
        )
        
        # Загружаем ссылки на документы
        document_links = self._load_document_links(
            tender_id=tender_id_for_query,
            registry_type=registry_type_for_query,
        )
        
        # Загружаем товары из сметы (tender_document_match_details)
        estimate_items = self._load_estimate_items(
            tender_id=tender_id_for_query,
            registry_type=registry_type_for_query,
        )
        
        # #region agent log
        logger.info(f"DealDetailService.build_deal_card: loaded found_phrases={len(found_phrases)}, document_links={len(document_links)}, estimate_items={len(estimate_items)}")
        # #endregion

        result = {
            "deal": deal_dict,
            "tender": tender_data,
            "customer": customer,
            "contractor": contractor,
            "contacts": {
                "customer": contacts_customer,
                "contractor": contacts_contractor,
                "deal": contacts_deal,
            },
            "items": deal_items,
            "found_phrases": found_phrases,
            "document_links": document_links,
            "estimate_items": estimate_items,
        }
        
        # Сохраняем в кеш
        if deal.id:
            self._deal_card_cache[deal.id] = result
            logger.debug(f"DealDetailService.build_deal_card: данные сохранены в кеш для deal_id={deal.id}")
        
        return result
    
    @classmethod
    def clear_cache(cls, deal_id: Optional[int] = None):
        """
        Очистка кеша данных карточек сделок.
        
        Args:
            deal_id: ID сделки для очистки конкретной записи. Если None - очищает весь кеш.
        """
        if deal_id:
            if deal_id in cls._deal_card_cache:
                del cls._deal_card_cache[deal_id]
                logger.debug(f"DealDetailService.clear_cache: очищен кеш для deal_id={deal_id}")
        else:
            cls._deal_card_cache.clear()
            logger.debug("DealDetailService.clear_cache: очищен весь кеш")

    @staticmethod
    def _extract_tender_data_from_metadata(deal: Deal) -> Dict[str, Any]:
        # #region agent log
        import json
        from pathlib import Path
        log_path = Path(r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "detail-dialog", "hypothesisId": "H2", "location": "deal_detail_service.py:_extract_tender_data:start", "message": "Extracting tender data from metadata", "data": {"deal_id": deal.id, "has_metadata": bool(deal.metadata), "metadata_type": str(type(deal.metadata))}, "timestamp": __import__('time').time_ns() // 1000000}) + "\n")
        # #endregion
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

        # #region agent log
        import json
        from pathlib import Path
        log_path = Path(r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "detail-dialog", "hypothesisId": "H3", "location": "deal_detail_service.py:_extract_tender_data:end", "message": "Tender data extracted", "data": {"original_keys": list(original.keys())[:30] if original else [], "has_customer": "customer" in original, "has_delivery_start": "delivery_start_date" in original, "has_delivery_end": "delivery_end_date" in original, "customer_value": original.get("customer"), "delivery_start": str(original.get("delivery_start_date")), "delivery_end": str(original.get("delivery_end_date"))}, "timestamp": __import__('time').time_ns() // 1000000}) + "\n")
        # #endregion

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

    def _load_stage_name(self, stage_id: int) -> Optional[str]:
        """Загрузка названия этапа воронки по ID (sales_pipeline_stages)."""
        try:
            rows = self.db_manager.execute_query(
                """
                SELECT name
                FROM sales_pipeline_stages
                WHERE id = %s
                """,
                (stage_id,),
                RealDictCursor,
            )
            if rows:
                return rows[0].get("name")
            return None
        except Exception as exc:  # pragma: no cover - защита от падения UI
            logger.error(f"Ошибка при загрузке названия этапа {stage_id}: {exc}", exc_info=True)
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

    def _load_found_phrases(
        self, tender_id: Optional[int], registry_type: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Загрузка найденных фраз из tender_document_match_details.
        
        Args:
            tender_id: ID закупки
            registry_type: Тип реестра ('44fz' или '223fz')
        
        Returns:
            Список найденных фраз (product_name из match_details)
        """
        if not tender_id or not registry_type:
            # #region agent log
            logger.warning(f"DealDetailService._load_found_phrases: пропуск, tender_id={tender_id}, registry_type={registry_type}")
            # #endregion
            return []
        
        try:
            # #region agent log
            logger.info(f"DealDetailService._load_found_phrases: начало загрузки для tender_id={tender_id}, registry_type={registry_type}")
            # #endregion
            # Сначала получаем match_id из tender_document_matches
            match_result = self.db_manager.execute_query(
                """
                SELECT id
                FROM tender_document_matches
                WHERE tender_id = %s AND registry_type = %s
                LIMIT 1
                """,
                (tender_id, registry_type),
                RealDictCursor,
            )
            
            if not match_result:
                # #region agent log
                logger.warning(f"DealDetailService._load_found_phrases: нет записи в tender_document_matches для tender_id={tender_id}, registry_type={registry_type}")
                # #endregion
                return []
            
            match_id = match_result[0]["id"]
            # #region agent log
            logger.info(f"DealDetailService._load_found_phrases: найден match_id={match_id}, загружаем детали")
            # #endregion
            
            # Получаем найденные фразы (product_name) из tender_document_match_details
            match_details = self.db_manager.execute_query(
                """
                SELECT DISTINCT product_name
                FROM tender_document_match_details
                WHERE match_id = %s AND product_name IS NOT NULL AND product_name != ''
                ORDER BY product_name
                """,
                (match_id,),
                RealDictCursor,
            )
            
            result = [dict(row) for row in match_details] if match_details else []
            # #region agent log
            logger.info(f"DealDetailService._load_found_phrases: загружено {len(result)} уникальных фраз")
            # #endregion
            return result
        except Exception as exc:
            logger.error(
                f"Ошибка при загрузке найденных фраз для tender_id={tender_id}, registry_type={registry_type}: {exc}",
                exc_info=True,
            )
            return []

    def _load_document_links(
        self, tender_id: Optional[int], registry_type: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Загрузка ссылок на документы из links_documentation_*_fz.
        
        Args:
            tender_id: ID закупки (contract_id в таблице links_documentation)
            registry_type: Тип реестра ('44fz' или '223fz')
        
        Returns:
            Список ссылок на документы
        """
        if not tender_id or not registry_type:
            # #region agent log
            logger.warning(f"DealDetailService._load_document_links: пропуск, tender_id={tender_id}, registry_type={registry_type}")
            # #endregion
            return []
        
        try:
            # #region agent log
            logger.info(f"DealDetailService._load_document_links: начало загрузки для tender_id={tender_id}, registry_type={registry_type}")
            # #endregion
            table_name = (
                "links_documentation_44_fz"
                if registry_type.lower() == "44fz"
                else "links_documentation_223_fz"
            )
            
            query = f"""
                SELECT 
                    id,
                    contract_id,
                    document_links,
                    file_name
                FROM {table_name}
                WHERE contract_id = %s
            """
            
            results = self.db_manager.execute_query(
                query, (tender_id,), RealDictCursor
            )
            
            result = [dict(row) for row in results] if results else []
            # #region agent log
            logger.info(f"DealDetailService._load_document_links: загружено {len(result)} ссылок на документы")
            # #endregion
            return result
        except Exception as exc:
            logger.error(
                f"Ошибка при загрузке ссылок на документы для tender_id={tender_id}, registry_type={registry_type}: {exc}",
                exc_info=True,
            )
            return []

    def _load_estimate_items(
        self, tender_id: Optional[int], registry_type: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Загрузка товаров из сметы (tender_document_match_details).
        
        Args:
            tender_id: ID закупки
            registry_type: Тип реестра ('44fz' или '223fz')
        
        Returns:
            Список товаров из сметы с данными из row_data (количество, цена, единица измерения и т.д.)
        """
        if not tender_id or not registry_type:
            # #region agent log
            logger.warning(f"DealDetailService._load_estimate_items: пропуск, tender_id={tender_id}, registry_type={registry_type}")
            # #endregion
            return []
        
        try:
            # #region agent log
            logger.info(f"DealDetailService._load_estimate_items: начало загрузки для tender_id={tender_id}, registry_type={registry_type}")
            # #endregion
            # Сначала получаем match_id из tender_document_matches
            match_result = self.db_manager.execute_query(
                """
                SELECT id
                FROM tender_document_matches
                WHERE tender_id = %s AND registry_type = %s
                LIMIT 1
                """,
                (tender_id, registry_type),
                RealDictCursor,
            )
            
            if not match_result:
                # #region agent log
                logger.warning(f"DealDetailService._load_estimate_items: нет записи в tender_document_matches")
                # #endregion
                return []
            
            match_id = match_result[0]["id"]
            
            # Получаем товары из сметы с данными из row_data
            match_details = self.db_manager.execute_query(
                """
                SELECT 
                    product_name,
                    matched_text,
                    matched_display_text,
                    row_data,
                    score,
                    sheet_name,
                    cell_address,
                    source_file
                FROM tender_document_match_details
                WHERE match_id = %s 
                  AND product_name IS NOT NULL 
                  AND product_name != ''
                ORDER BY score DESC, product_name
                """,
                (match_id,),
                RealDictCursor,
            )
            
            # Парсим row_data (JSON) и извлекаем количество, цену, единицу измерения
            estimate_items = []
            for detail in match_details:
                item = {
                    "product_name": detail.get("product_name", ""),
                    "matched_text": detail.get("matched_text", ""),
                    "matched_display_text": detail.get("matched_display_text", ""),
                    "score": detail.get("score", 0),
                    "sheet_name": detail.get("sheet_name", ""),
                    "cell_address": detail.get("cell_address", ""),
                    "source_file": detail.get("source_file", ""),
                }
                
                # Парсим row_data (JSONB)
                row_data = detail.get("row_data")
                if row_data:
                    import json
                    if isinstance(row_data, str):
                        try:
                            row_data = json.loads(row_data)
                        except Exception as parse_exc:
                            # #region agent log
                            logger.warning(f"DealDetailService._load_estimate_items: ошибка парсинга row_data: {parse_exc}")
                            # #endregion
                            row_data = {}
                    
                    # Извлекаем количество, цену, единицу измерения из row_data
                    # Обычно в сметах это могут быть поля: "Количество", "Цена", "Единица измерения", "Сумма" и т.д.
                    if isinstance(row_data, dict):
                        # #region agent log
                        logger.debug(f"DealDetailService._load_estimate_items: row_data keys={list(row_data.keys())[:10]}")
                        # #endregion
                        # Ищем количество (может быть в разных полях)
                        quantity = (
                            row_data.get("Количество") or 
                            row_data.get("количество") or 
                            row_data.get("Кол-во") or 
                            row_data.get("кол-во") or
                            row_data.get("quantity") or
                            None
                        )
                        
                        # Ищем цену
                        price = (
                            row_data.get("Цена") or 
                            row_data.get("цена") or 
                            row_data.get("Цена за единицу") or
                            row_data.get("price") or
                            row_data.get("price_per_unit") or
                            None
                        )
                        
                        # Ищем единицу измерения
                        unit = (
                            row_data.get("Единица измерения") or 
                            row_data.get("единица измерения") or 
                            row_data.get("Ед.") or 
                            row_data.get("ед.") or
                            row_data.get("unit") or
                            row_data.get("Ед. изм.") or
                            None
                        )
                        
                        # Ищем сумму
                        total = (
                            row_data.get("Сумма") or 
                            row_data.get("сумма") or 
                            row_data.get("Итого") or
                            row_data.get("total") or
                            row_data.get("total_price") or
                            None
                        )
                        
                        item["quantity"] = quantity
                        item["price_per_unit"] = price
                        item["unit"] = unit
                        item["total_price"] = total
                        item["row_data"] = row_data  # Сохраняем полные данные для отладки
                
                estimate_items.append(item)
            
            # #region agent log
            logger.info(f"DealDetailService._load_estimate_items: загружено {len(estimate_items)} товаров из сметы")
            # #endregion
            return estimate_items
        except Exception as exc:
            logger.error(
                f"Ошибка при загрузке товаров из сметы для tender_id={tender_id}, registry_type={registry_type}: {exc}",
                exc_info=True,
            )
            return []

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


