"""
Упрощённый фасад для работы с тендерами.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from loguru import logger
from psycopg2.extras import RealDictCursor

from core.tender_database import TenderDatabaseManager
from services.tender_repositories.okpd_repository import OkpdRepository
from services.tender_repositories.user_okpd_repository import UserOkpdRepository
from services.tender_repositories.okpd_category_repository import OkpdCategoryRepository
from services.tender_repositories.stop_words_repository import StopWordsRepository
from services.tender_repositories.document_stop_phrases_repository import DocumentStopPhrasesRepository
from services.tender_repositories.region_repository import RegionRepository
from services.tender_repositories.tender_documents_repository import TenderDocumentsRepository
from services.tender_repositories.tender_query_builder import TenderQueryBuilder
from services.tender_repositories.feeds.feed_filters import FeedFilters, WonFilters
from services.tender_repositories.feeds.new_tenders_service import NewTendersService
from services.tender_repositories.feeds.won_tenders_service import WonTendersService


class TenderRepository:
    """Фасад, делегирующий работу специализированным сервисам."""
    
    def __init__(self, db_manager: TenderDatabaseManager):
        self.db_manager = db_manager
        self.okpd_repo = OkpdRepository(db_manager)
        self.user_okpd_repo = UserOkpdRepository(db_manager)
        self.okpd_category_repo = OkpdCategoryRepository(db_manager)
        self.stop_words_repo = StopWordsRepository(db_manager)
        self.document_stop_phrases_repo = DocumentStopPhrasesRepository(db_manager)
        self.region_repo = RegionRepository(db_manager)
        self.tender_documents_repo = TenderDocumentsRepository(db_manager)
        self.new_service = NewTendersService(db_manager, self.tender_documents_repo)
        self.won_service = WonTendersService(db_manager, self.tender_documents_repo)

    # --- OKPD / регионы / стоп-слова --------------------------------------------------
    def search_okpd_codes(self, search_text: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        return self.okpd_repo.search_okpd_codes(search_text, limit)
    
    def get_all_okpd_codes(self, limit: int = 500) -> List[Dict[str, Any]]:
        return self.okpd_repo.get_all_okpd_codes(limit)
    
    def get_user_okpd_codes(self, user_id: int, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.user_okpd_repo.get_user_okpd_codes(user_id, category_id)

    def add_user_okpd_code(self, user_id: int, okpd_code: str, name: Optional[str] = None, setting_id: Optional[int] = None) -> Optional[int]:
        return self.user_okpd_repo.add_user_okpd_code(user_id, okpd_code, name, setting_id)
    
    def remove_user_okpd_code(self, user_id: int, okpd_id: int) -> bool:
        return self.user_okpd_repo.remove_user_okpd_code(user_id, okpd_id)
    
    def get_okpd_by_code(self, okpd_code: str) -> Optional[Dict[str, Any]]:
        return self.okpd_repo.get_okpd_by_code(okpd_code)
    
    def get_all_regions(self) -> List[Dict[str, Any]]:
        return self.region_repo.get_all_regions()

    def search_okpd_codes_by_region(self, search_text: Optional[str], region_id: Optional[int], limit: int = 100) -> List[Dict[str, Any]]:
        return self.okpd_repo.search_okpd_codes_by_region(search_text, region_id, limit)
    
    def get_user_stop_words(self, user_id: int) -> List[Dict[str, Any]]:
        return self.stop_words_repo.get_user_stop_words(user_id)

    def add_user_stop_words(self, user_id: int, stop_words: List[str], setting_id: Optional[int] = None) -> Dict[str, Any]:
        return self.stop_words_repo.add_user_stop_words(user_id, stop_words, setting_id)
    
    def remove_user_stop_word(self, user_id: int, stop_word_id: int) -> bool:
        return self.stop_words_repo.remove_user_stop_word(user_id, stop_word_id)

    # --- Стоп-фразы для анализа документации -------------------------------------------
    def get_document_stop_phrases(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получение стоп-фраз анализа документации для пользователя.
        """
        return self.document_stop_phrases_repo.get_document_stop_phrases(user_id)

    def add_document_stop_phrases(
        self,
        user_id: int,
        phrases: List[str],
        setting_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Добавление стоп-фраз анализа документации для пользователя.
        """
        return self.document_stop_phrases_repo.add_document_stop_phrases(
            user_id,
            phrases,
            setting_id,
        )

    def remove_document_stop_phrase(self, user_id: int, phrase_id: int) -> bool:
        """
        Удаление стоп-фразы анализа документации.
        """
        return self.document_stop_phrases_repo.remove_document_stop_phrase(
            user_id,
            phrase_id,
        )

    # --- Публичные фиды ----------------------------------------------------------------
    def get_new_tenders_44fz(self, user_id: int, user_okpd_codes: Optional[List[str]] = None, user_stop_words: Optional[List[str]] = None,
                              region_id: Optional[int] = None, category_id: Optional[int] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        return self._fetch_new_feed("44fz", user_id, user_okpd_codes, user_stop_words, region_id, category_id, limit)

    def get_new_tenders_223fz(self, user_id: int, user_okpd_codes: Optional[List[str]] = None, user_stop_words: Optional[List[str]] = None,
                              region_id: Optional[int] = None, category_id: Optional[int] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        return self._fetch_new_feed("223fz", user_id, user_okpd_codes, user_stop_words, region_id, category_id, limit)

    def get_won_tenders_44fz(self, user_id: int, user_okpd_codes: Optional[List[str]] = None, user_stop_words: Optional[List[str]] = None,
                              region_id: Optional[int] = None, category_id: Optional[int] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        return self._fetch_won_feed("44fz", user_id, user_okpd_codes, user_stop_words, region_id, category_id, limit)

    def get_won_tenders_223fz(self, user_id: int, user_okpd_codes: Optional[List[str]] = None, user_stop_words: Optional[List[str]] = None,
                               region_id: Optional[int] = None, category_id: Optional[int] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        return self._fetch_won_feed("223fz", user_id, user_okpd_codes, user_stop_words, region_id, category_id, limit)
    
    def get_commission_tenders_44fz(self, user_id: int, user_okpd_codes: Optional[List[str]] = None, user_stop_words: Optional[List[str]] = None,
                                      region_id: Optional[int] = None, category_id: Optional[int] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Получение закупок 44ФЗ со статусом "Работа комиссии" (status_id = 2)
        """
        return self._fetch_commission_feed("44fz", user_id, user_okpd_codes, user_stop_words, region_id, category_id, limit)

    # --- Документы ---------------------------------------------------------------------
    def get_tender_documents(self, tender_id: int, registry_type: str) -> List[Dict[str, Any]]:
        return self.tender_documents_repo.get_tender_documents(tender_id, registry_type)

    def get_tenders_by_ids(self, tender_ids_44fz: Optional[List[int]] = None, tender_ids_223fz: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        tenders: List[Dict[str, Any]] = []
        if tender_ids_44fz:
            tenders.extend(self._fetch_registry_records("44fz", tender_ids_44fz))
        if tender_ids_223fz:
            tenders.extend(self._fetch_registry_records("223fz", tender_ids_223fz))
        self._attach_documents(tenders)
        return tenders
    
    # --- Категории ОКПД ----------------------------------------------------------------
    def get_okpd_categories(self, user_id: int) -> List[Dict[str, Any]]:
        return self.okpd_category_repo.get_okpd_categories(user_id)

    def create_okpd_category(self, user_id: int, name: str, description: Optional[str] = None) -> Optional[int]:
        return self.okpd_category_repo.create_okpd_category(user_id, name, description)

    def update_okpd_category(self, category_id: int, user_id: int, name: Optional[str] = None, description: Optional[str] = None) -> bool:
        return self.okpd_category_repo.update_okpd_category(category_id, user_id, name, description)
    
    def delete_okpd_category(self, category_id: int, user_id: int) -> bool:
        return self.okpd_category_repo.delete_okpd_category(category_id, user_id)

    def assign_okpd_to_category(self, user_id: int, okpd_id: int, category_id: Optional[int] = None) -> bool:
        return self.okpd_category_repo.assign_okpd_to_category(user_id, okpd_id, category_id)

    def get_okpd_codes_by_category(self, user_id: int, category_id: Optional[int] = None) -> List[str]:
        return self.okpd_category_repo.get_okpd_codes_by_category(user_id, category_id)

    # --- Внутренние помощники ----------------------------------------------------------
    def _fetch_new_feed(self, registry: str, user_id: int, okpd_codes: Optional[List[str]], stop_words: Optional[List[str]],
                        region_id: Optional[int], category_id: Optional[int], limit: int) -> List[Dict[str, Any]]:
        effective_stop_words = stop_words or []
        if effective_stop_words:
            logger.info(f"Передано стоп-слов в _fetch_new_feed ({registry}): {len(effective_stop_words)}")
        else:
            logger.warning(f"Стоп-слова не переданы в _fetch_new_feed ({registry}): stop_words={stop_words}")
        
        return self._fetch_feed(
            registry=registry,
            user_id=user_id,
            okpd_codes=okpd_codes,
            stop_words=effective_stop_words,
            region_id=region_id,
            category_id=category_id,
            limit=limit,
            filter_class=FeedFilters,
            fetch_method=lambda f, r: self.new_service.fetch_44fz(f) if r == "44fz" else self.new_service.fetch_223fz(f),
            error_context="новых торгов"
        )

    def _fetch_commission_feed(self, registry: str, user_id: int, okpd_codes: Optional[List[str]], stop_words: Optional[List[str]],
                                region_id: Optional[int], category_id: Optional[int], limit: int) -> List[Dict[str, Any]]:
        """Загрузка закупок со статусом 'Работа комиссии' (status_id = 2)"""
        if registry != "44fz":
            return []  # Для 223ФЗ пока нет статуса "Работа комиссии"
        
        return self._fetch_feed(
            registry=registry,
            user_id=user_id,
            okpd_codes=okpd_codes,
            stop_words=stop_words or [],
            region_id=region_id,
            category_id=category_id,
            limit=limit,
            filter_class=FeedFilters,
            fetch_method=lambda f, r: self.new_service.fetch_commission_44fz(f),
            error_context="закупок 'Работа комиссии'"
        )
    
    def _fetch_won_feed(self, registry: str, user_id: int, okpd_codes: Optional[List[str]], stop_words: Optional[List[str]],
                        region_id: Optional[int], category_id: Optional[int], limit: int) -> List[Dict[str, Any]]:
        return self._fetch_feed(
            registry=registry,
            user_id=user_id,
            okpd_codes=okpd_codes,
            stop_words=stop_words or [],
            region_id=region_id,
            category_id=category_id,
            limit=limit,
            filter_class=WonFilters,
            fetch_method=lambda f, r: self.won_service.fetch_44fz(f) if r == "44fz" else self.won_service.fetch_223fz(f),
            error_context="разыгранных торгов"
        )
    
    def _fetch_feed(
        self,
        registry: str,
        user_id: int,
        okpd_codes: Optional[List[str]],
        stop_words: List[str],
        region_id: Optional[int],
        category_id: Optional[int],
        limit: int,
        filter_class: type,
        fetch_method: callable,
        error_context: str
    ) -> List[Dict[str, Any]]:
        """Общий метод для загрузки фидов"""
        try:
            resolved_codes = self._resolve_okpd_codes(user_id, category_id, okpd_codes)
            if not resolved_codes:
                return []
            
            filters = filter_class(
                user_id=user_id,
                okpd_codes=resolved_codes,
                stop_words=stop_words,
                region_id=region_id,
                category_id=category_id,
                limit=limit,
            )
            return fetch_method(filters, registry)
        except Exception as error:
            logger.error(f"Ошибка при загрузке {error_context} {registry}: {error}", exc_info=True)
            return []

    def _resolve_okpd_codes(self, user_id: int, category_id: Optional[int], fallback: Optional[List[str]]) -> List[str]:
        if category_id is not None:
            return self.okpd_category_repo.get_okpd_codes_by_category(user_id, category_id)
        return fallback or []

    def _fetch_registry_records(self, registry_type: str, tender_ids: List[int]) -> List[Dict[str, Any]]:
        placeholders = ",".join(["%s"] * len(tender_ids))
        table_name = TenderQueryBuilder.resolve_registry_table(registry_type)
        query = f"""
            SELECT r.*, '{registry_type}' as registry_type
            FROM {table_name} r
            WHERE r.id IN ({placeholders})
        """
        try:
            results = self.db_manager.execute_query(query, tuple(tender_ids), RealDictCursor)
            return [dict(row) for row in results] if results else []
        except Exception as error:
            logger.error("Ошибка при получении торгов %s по ID: %s", registry_type, error)
            return []

    def _attach_documents(self, tenders: List[Dict[str, Any]]) -> None:
        """Прикрепление документов к торгам"""
        ids_by_registry = {"44fz": [], "223fz": []}
        for tender in tenders:
            registry = tender.get("registry_type")
            if registry in ids_by_registry:
                ids_by_registry[registry].append(tender["id"])
        
        docs_by_registry = {}
        if ids_by_registry["44fz"]:
            docs_by_registry["44fz"] = self.tender_documents_repo.get_tender_documents_44fz_batch(ids_by_registry["44fz"])
        if ids_by_registry["223fz"]:
            docs_by_registry["223fz"] = self.tender_documents_repo.get_tender_documents_223fz_batch(ids_by_registry["223fz"])
        
        for tender in tenders:
            registry = tender.get("registry_type")
            tender["document_links"] = docs_by_registry.get(registry, {}).get(tender["id"], [])

