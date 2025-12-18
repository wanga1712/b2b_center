"""
Базовый сервис для формирования и выполнения запросов по тендерам.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from loguru import logger
from psycopg2.extras import RealDictCursor

from core.tender_database import TenderDatabaseManager
from services.tender_repositories.tender_documents_repository import TenderDocumentsRepository
from services.tender_repositories.tender_query_builder import TenderQueryBuilder
from services.tender_repositories.feeds.feed_filters import FeedFilters


class BaseFeedService:
    """Общий функционал для выборки тендеров разных типов."""

    def __init__(
        self,
        db_manager: TenderDatabaseManager,
        documents_repo: TenderDocumentsRepository,
    ):
        self.db_manager = db_manager
        self.documents_repo = documents_repo

    def execute_feed_query(
        self,
        select_query: str,
        select_params: List[Any],
        count_query: str,
        count_params: List[Any],
        registry_type: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        results = self.db_manager.execute_query(
            select_query,
            tuple(select_params) if select_params else None,
            RealDictCursor,
        )
        tenders = [dict(row) for row in results] if results else []

        total_count = self._fetch_total_count(count_query, count_params)
        total = total_count if total_count is not None else "неизвестно"
        logger.info(f"Загружено торгов {registry_type}: {len(tenders)} из {total}")

        if tenders:
            tender_ids = [t["id"] for t in tenders]
            documents = self._load_documents_batch(tender_ids, registry_type)
            for tender in tenders:
                tender["document_links"] = documents.get(tender["id"], [])

            if total_count is not None:
                tenders[0]["_total_count"] = total_count
                tenders[0]["_loaded_count"] = len(tenders)
            else:
                inferred = len(tenders) if not limit or len(tenders) < limit else None
                tenders[0]["_total_count"] = inferred
                tenders[0]["_loaded_count"] = len(tenders)

        return tenders

    def _fetch_total_count(self, query: str, params: List[Any]) -> Optional[int]:
        if not query:
            return None
        try:
            result = self.db_manager.execute_query(query, tuple(params), RealDictCursor)
            return result[0].get("total_count") if result else None
        except Exception as error:
            logger.debug("Не удалось получить общее количество: %s", error)
            return None

    def _load_documents_batch(self, tender_ids: List[int], registry_type: str) -> Dict[int, List[Dict[str, Any]]]:
        if not tender_ids:
            return {}
        if registry_type == "223fz":
            return self.documents_repo.get_tender_documents_223fz_batch(tender_ids)
        return self.documents_repo.get_tender_documents_44fz_batch(tender_ids)

