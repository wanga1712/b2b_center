"""
MODULE: modules.crm.sales_funnel.deal_item_repository
RESPONSIBILITY: Repository for deal items (materials, works).
ALLOWED: typing, loguru, psycopg2, core.tender_database.
FORBIDDEN: Business logic, UI.
ERRORS: None.

Репозиторий для работы с позициями сделки (deal_item).
"""

from typing import List, Dict, Any, Optional
from loguru import logger
from psycopg2.extras import RealDictCursor
from core.tender_database import TenderDatabaseManager


class DealItemRepository:
    """Репозиторий для работы с позициями сделки (материалы, работы, товары КП)."""

    def __init__(self, db_manager: TenderDatabaseManager):
        self.db_manager = db_manager

    def get_items_by_deal(
        self, deal_id: int, item_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение позиций сделки по ID сделки.

        Args:
            deal_id: ID сделки
            item_type: Тип позиций ('материал', 'работа', 'товар_кп'), None = все

        Returns:
            Список позиций сделки
        """
        try:
            if item_type:
                query = """
                    SELECT 
                        id, deal_id, product_name, product_code, is_analog,
                        unit, quantity, price_per_unit, total_price, comment,
                        item_type, created_at, updated_at
                    FROM deal_item
                    WHERE deal_id = %s AND item_type = %s
                    ORDER BY id ASC
                """
                params = (deal_id, item_type)
            else:
                query = """
                    SELECT 
                        id, deal_id, product_name, product_code, is_analog,
                        unit, quantity, price_per_unit, total_price, comment,
                        item_type, created_at, updated_at
                    FROM deal_item
                    WHERE deal_id = %s
                    ORDER BY item_type, id ASC
                """
                params = (deal_id,)

            results = self.db_manager.execute_query(query, params, RealDictCursor)
            return [dict(row) for row in results] if results else []
        except Exception as exc:
            logger.error(
                f"Ошибка при загрузке позиций сделки {deal_id}, type={item_type}: {exc}",
                exc_info=True,
            )
            return []

    def save_items(self, deal_id: int, items: List[Dict[str, Any]], item_type: str) -> bool:
        """
        Сохранение позиций сделки (материалы или работы).

        Args:
            deal_id: ID сделки
            items: Список позиций для сохранения
            item_type: Тип позиций ('материал' или 'работа')

        Returns:
            True при успехе, False при ошибке
        """
        try:
            # Удаляем существующие позиции этого типа
            self.db_manager.execute_query(
                "DELETE FROM deal_item WHERE deal_id = %s AND item_type = %s",
                (deal_id, item_type),
            )

            # Вставляем новые позиции
            for item in items:
                product_name = item.get("product_name", "")
                unit = item.get("unit", "шт")
                quantity = item.get("quantity", 0)
                price_per_unit = item.get("price_per_unit", 0)
                comment = item.get("comment", "")

                if not product_name or quantity <= 0:
                    continue  # Пропускаем пустые строки

                self.db_manager.execute_query(
                    """
                    INSERT INTO deal_item (
                        deal_id, product_name, unit, quantity, price_per_unit, 
                        item_type, comment
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (deal_id, product_name, unit, quantity, price_per_unit, item_type, comment),
                )

            logger.info(
                f"Сохранено {len(items)} позиций типа '{item_type}' для сделки {deal_id}"
            )
            return True
        except Exception as exc:
            logger.error(
                f"Ошибка при сохранении позиций сделки {deal_id}, type={item_type}: {exc}",
                exc_info=True,
            )
            return False

    def delete_items(self, deal_id: int, item_type: str) -> bool:
        """
        Удаление позиций сделки определенного типа.

        Args:
            deal_id: ID сделки
            item_type: Тип позиций ('материал', 'работа', 'товар_кп')

        Returns:
            True при успехе, False при ошибке
        """
        try:
            self.db_manager.execute_query(
                "DELETE FROM deal_item WHERE deal_id = %s AND item_type = %s",
                (deal_id, item_type),
            )
            logger.info(f"Удалены позиции типа '{item_type}' для сделки {deal_id}")
            return True
        except Exception as exc:
            logger.error(
                f"Ошибка при удалении позиций сделки {deal_id}, type={item_type}: {exc}",
                exc_info=True,
            )
            return False

