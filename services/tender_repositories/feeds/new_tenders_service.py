"""
Сервис загрузки новых тендеров 44ФЗ и 223ФЗ.
"""

from __future__ import annotations

from datetime import date
from typing import List, Dict, Any, Optional

from loguru import logger
from psycopg2.extras import RealDictCursor

from core.tender_database import TenderDatabaseManager
from services.tender_repositories.tender_documents_repository import TenderDocumentsRepository
from services.tender_repositories.tender_query_builder import TenderQueryBuilder
from services.tender_repositories.feeds.feed_filters import FeedFilters
from services.tender_repositories.feeds.base_feed_service import BaseFeedService


class NewTendersService(BaseFeedService):
    """Обрабатывает запросы для вкладок новых тендеров."""

    def __init__(
        self,
        db_manager: TenderDatabaseManager,
        documents_repo: TenderDocumentsRepository,
    ):
        super().__init__(db_manager, documents_repo)

    def fetch_44fz(self, filters: FeedFilters) -> List[Dict[str, Any]]:
        okpd_ids = self._resolve_okpd_ids(filters.okpd_codes)
        if not okpd_ids:
            logger.info("Нет ОКПД кодов для пользователя %s (44ФЗ)", filters.user_id)
            return []

        select_query, select_params = self._build_new_query("44fz", filters, okpd_ids)
        count_query, count_params = self._build_new_count_query("44fz", filters, okpd_ids)
        return self.execute_feed_query(
            select_query,
            select_params,
            count_query,
            count_params,
            registry_type="44fz",
            limit=filters.limit,
        )

    def fetch_223fz(self, filters: FeedFilters) -> List[Dict[str, Any]]:
        okpd_ids = self._resolve_okpd_ids(filters.okpd_codes)
        if not okpd_ids:
            logger.info("Нет ОКПД кодов для пользователя %s (223ФЗ)", filters.user_id)
            return []

        select_query, select_params = self._build_new_query("223fz", filters, okpd_ids)
        count_query, count_params = self._build_new_count_query("223fz", filters, okpd_ids)
        return self.execute_feed_query(
            select_query,
            select_params,
            count_query,
            count_params,
            registry_type="223fz",
            limit=filters.limit,
        )
    
    def fetch_commission_44fz(self, filters: FeedFilters) -> List[Dict[str, Any]]:
        """
        Загрузка закупок 44ФЗ со статусом "Работа комиссии" (status_id = 2)
        """
        okpd_ids = self._resolve_okpd_ids(filters.okpd_codes)
        if not okpd_ids:
            logger.info("Нет ОКПД кодов для пользователя %s (Работа комиссии 44ФЗ)", filters.user_id)
            return []

        select_query, select_params = self._build_commission_query("44fz", filters, okpd_ids)
        count_query, count_params = self._build_commission_count_query("44fz", filters, okpd_ids)
        return self.execute_feed_query(
            select_query,
            select_params,
            count_query,
            count_params,
            registry_type="44fz",
            limit=filters.limit,
        )

    def _build_new_query(
        self,
        registry_type: str,
        filters: FeedFilters,
        okpd_ids: List[int],
    ) -> tuple[str, List[Any]]:
        select_fields = TenderQueryBuilder.build_base_select_fields()
        table_name = TenderQueryBuilder.resolve_registry_table(registry_type)
        base_joins = TenderQueryBuilder.build_base_joins(table_name, registry_type)
        query = f"SELECT DISTINCT {select_fields} {base_joins} WHERE 1=1"
        params: List[Any] = []

        # Используем статусы вместо дат для ускорения (после миграции)
        today = date.today()
        new_filter, new_params = TenderQueryBuilder.build_new_tenders_filter(today, use_status=True)
        query += new_filter
        params.extend(new_params)

        placeholders = ",".join(["%s"] * len(okpd_ids))
        query += f" AND r.okpd_id IN ({placeholders})"
        params.extend(okpd_ids)

        region_filter, region_params = TenderQueryBuilder.build_region_filter(filters.region_id)
        query += region_filter
        params.extend(region_params)

        stop_filter, stop_params = TenderQueryBuilder.build_stop_words_filter(filters.stop_words)
        query += stop_filter
        params.extend(stop_params)

        # Для 223ФЗ добавляем фильтр по статусам (исключаем "Плохие")
        if registry_type == "223fz":
            query += TenderQueryBuilder.build_status_filter_223fz()

        query += TenderQueryBuilder.build_is_interesting_filter(registry_type)
        query += TenderQueryBuilder.build_order_by()

        if filters.limit and filters.limit > 0:
            query += " LIMIT %s"
            params.append(filters.limit)

        # Логируем SQL запрос для отладки
        logger.debug(f"SQL запрос для новых торгов {registry_type}:\n{query}\nПараметры: {params}")

        return query, params

    def _build_new_count_query(
        self,
        registry_type: str,
        filters: FeedFilters,
        okpd_ids: List[int],
    ) -> tuple[str, List[Any]]:
        today = date.today()
        table_name = TenderQueryBuilder.resolve_registry_table(registry_type)
        select = (
            f"SELECT COUNT(DISTINCT r.id) as total_count FROM {table_name} r "
            "LEFT JOIN customer c ON r.customer_id = c.id "
            "LEFT JOIN region reg ON r.region_id = reg.id "
            "LEFT JOIN contractor cont ON r.contractor_id = cont.id "
            "LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id "
            "LEFT JOIN trading_platform tp ON r.trading_platform_id = tp.id "
            "LEFT JOIN tender_document_matches tdm ON tdm.tender_id = r.id "
            f"AND tdm.registry_type = '{registry_type}' "
            "WHERE 1=1"
        )
        params: List[Any] = []
        # Используем статусы вместо дат для ускорения (после миграции)
        new_filter, new_params = TenderQueryBuilder.build_new_tenders_filter(today, use_status=True)
        query = select + new_filter
        params.extend(new_params)

        placeholders = ",".join(["%s"] * len(okpd_ids))
        query += f" AND r.okpd_id IN ({placeholders})"
        params.extend(okpd_ids)

        region_filter, region_params = TenderQueryBuilder.build_region_filter(filters.region_id)
        query += region_filter
        params.extend(region_params)

        stop_filter, stop_params = TenderQueryBuilder.build_stop_words_filter(filters.stop_words)
        query += stop_filter
        params.extend(stop_params)

        # Для 223ФЗ добавляем фильтр по статусам (исключаем "Плохие")
        if registry_type == "223fz":
            query += TenderQueryBuilder.build_status_filter_223fz()

        query += TenderQueryBuilder.build_is_interesting_filter(registry_type)
        
        # Логируем SQL запрос для отладки
        logger.debug(f"SQL запрос COUNT для новых торгов {registry_type}:\n{query}\nПараметры: {params}")
        
        return query, params

    def _build_commission_query(
        self,
        registry_type: str,
        filters: FeedFilters,
        okpd_ids: List[int],
    ) -> tuple[str, List[Any]]:
        """
        Построение запроса для закупок со статусом "Работа комиссии" (status_id = 2)
        """
        select_fields = TenderQueryBuilder.build_base_select_fields()
        table_name = TenderQueryBuilder.resolve_registry_table(registry_type)
        base_joins = TenderQueryBuilder.build_base_joins(table_name, registry_type)
        query = f"SELECT DISTINCT {select_fields} {base_joins} WHERE 1=1"
        params: List[Any] = []

        # Используем фильтр по статусу "Работа комиссии"
        commission_filter, commission_params = TenderQueryBuilder.build_commission_tenders_filter(use_status=True)
        query += commission_filter
        params.extend(commission_params)

        placeholders = ",".join(["%s"] * len(okpd_ids))
        query += f" AND r.okpd_id IN ({placeholders})"
        params.extend(okpd_ids)

        region_filter, region_params = TenderQueryBuilder.build_region_filter(filters.region_id)
        query += region_filter
        params.extend(region_params)

        stop_filter, stop_params = TenderQueryBuilder.build_stop_words_filter(filters.stop_words)
        query += stop_filter
        params.extend(stop_params)

        query += TenderQueryBuilder.build_is_interesting_filter(registry_type)
        query += TenderQueryBuilder.build_order_by()

        if filters.limit and filters.limit > 0:
            query += " LIMIT %s"
            params.append(filters.limit)

        logger.debug(f"SQL запрос для работы комиссии {registry_type}:\n{query}\nПараметры: {params}")

        return query, params
    
    def _build_commission_count_query(
        self,
        registry_type: str,
        filters: FeedFilters,
        okpd_ids: List[int],
    ) -> tuple[str, List[Any]]:
        """
        Построение COUNT запроса для закупок со статусом "Работа комиссии"
        """
        table_name = TenderQueryBuilder.resolve_registry_table(registry_type)
        select = (
            f"SELECT COUNT(DISTINCT r.id) as total_count FROM {table_name} r "
            "LEFT JOIN customer c ON r.customer_id = c.id "
            "LEFT JOIN region reg ON r.region_id = reg.id "
            "LEFT JOIN contractor cont ON r.contractor_id = cont.id "
            "LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id "
            "LEFT JOIN trading_platform tp ON r.trading_platform_id = tp.id "
            "LEFT JOIN tender_document_matches tdm ON tdm.tender_id = r.id "
            f"AND tdm.registry_type = '{registry_type}' "
            "WHERE 1=1"
        )
        params: List[Any] = []
        
        commission_filter, commission_params = TenderQueryBuilder.build_commission_tenders_filter(use_status=True)
        query = select + commission_filter
        params.extend(commission_params)

        placeholders = ",".join(["%s"] * len(okpd_ids))
        query += f" AND r.okpd_id IN ({placeholders})"
        params.extend(okpd_ids)

        region_filter, region_params = TenderQueryBuilder.build_region_filter(filters.region_id)
        query += region_filter
        params.extend(region_params)

        stop_filter, stop_params = TenderQueryBuilder.build_stop_words_filter(filters.stop_words)
        query += stop_filter
        params.extend(stop_params)

        query += TenderQueryBuilder.build_is_interesting_filter(registry_type)
        
        logger.debug(f"SQL запрос COUNT для работы комиссии {registry_type}:\n{query}\nПараметры: {params}")
        
        return query, params

    def _resolve_okpd_ids(self, user_okpd_codes: List[str]) -> List[int]:
        if not user_okpd_codes:
            return []
        query = """
            SELECT DISTINCT id FROM collection_codes_okpd
            WHERE main_code = ANY(%s) OR sub_code = ANY(%s)
        """
        results = self.db_manager.execute_query(
            query,
            (user_okpd_codes, user_okpd_codes),
            RealDictCursor,
        )
        return [row["id"] for row in results if row.get("id")] if results else []

