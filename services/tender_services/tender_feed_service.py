"""
Сервис для работы с фидами тендеров.

Отвечает за:
- Получение новых тендеров
- Получение выигранных тендеров  
- Получение комиссионных тендеров
- Фильтрация и обработка фидов
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from core.tender_database import TenderDatabaseManager
from services.tender_repositories.tender_documents_repository import TenderDocumentsRepository
from services.tender_repositories.feeds.new_tenders_service import NewTendersService
from services.tender_repositories.feeds.won_tenders_service import WonTendersService
from services.tender_repositories.feeds.feed_filters import FeedFilters, WonFilters


class TenderFeedService:
    """Сервис для работы с фидами тендеров."""
    
    def __init__(self, db_manager: TenderDatabaseManager):
        self.db_manager = db_manager
        self.tender_documents_repo = TenderDocumentsRepository(db_manager)
        self.new_service = NewTendersService(db_manager, self.tender_documents_repo)
        self.won_service = WonTendersService(db_manager, self.tender_documents_repo)
    
    def get_new_tenders_44fz(self, user_id: int, user_okpd_codes: Optional[List[str]] = None, 
                           user_stop_words: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Получение новых тендеров 44-ФЗ."""
        return self.new_service.get_new_tenders_44fz(user_id, user_okpd_codes, user_stop_words)
    
    def get_new_tenders_223fz(self, user_id: int, user_okpd_codes: Optional[List[str]] = None, 
                            user_stop_words: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Получение новых тендеров 223-ФЗ."""
        return self.new_service.get_new_tenders_223fz(user_id, user_okpd_codes, user_stop_words)
    
    def get_won_tenders_44fz(self, user_id: int, user_okpd_codes: Optional[List[str]] = None, 
                           user_stop_words: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Получение выигранных тендеров 44-ФЗ."""
        return self.won_service.get_won_tenders_44fz(user_id, user_okpd_codes, user_stop_words)
    
    def get_won_tenders_223fz(self, user_id: int, user_okpd_codes: Optional[List[str]] = None, 
                            user_stop_words: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Получение выигранных тендеров 223-ФЗ."""
        return self.won_service.get_won_tenders_223fz(user_id, user_okpd_codes, user_stop_words)
    
    def get_commission_tenders_44fz(self, user_id: int, user_okpd_codes: Optional[List[str]] = None, 
                                  user_stop_words: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Получение комиссионных тендеров 44-ФЗ."""
        return self._fetch_commission_feed('44fz', user_id, user_okpd_codes, user_stop_words)
    
    def _fetch_new_feed(self, registry: str, user_id: int, okpd_codes: Optional[List[str]], 
                      stop_words: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Внутренний метод для получения новых тендеров."""
        if registry == '44fz':
            return self.new_service.get_new_tenders_44fz(user_id, okpd_codes, stop_words)
        else:
            return self.new_service.get_new_tenders_223fz(user_id, okpd_codes, stop_words)
    
    def _fetch_commission_feed(self, registry: str, user_id: int, okpd_codes: Optional[List[str]], 
                             stop_words: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Внутренний метод для получения комиссионных тендеров."""
        # Используем базовую фильтрацию как для новых тендеров
        filters = FeedFilters(
            user_id=user_id,
            okpd_codes=okpd_codes,
            stop_words=stop_words
        )
        
        # Здесь должна быть логика для комиссионных тендеров
        # Временно возвращаем пустой список
        return []
    
    def _fetch_won_feed(self, registry: str, user_id: int, okpd_codes: Optional[List[str]], 
                      stop_words: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Внутренный метод для получения выигранных тендеров."""
        if registry == '44fz':
            return self.won_service.get_won_tenders_44fz(user_id, okpd_codes, stop_words)
        else:
            return self.won_service.get_won_tenders_223fz(user_id, okpd_codes, stop_words)
    
    def _fetch_feed(self, registry: str, feed_type: str, user_id: int, 
                   okpd_codes: Optional[List[str]], stop_words: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Универсальный метод для получения фидов."""
        if feed_type == 'new':
            return self._fetch_new_feed(registry, user_id, okpd_codes, stop_words)
        elif feed_type == 'won':
            return self._fetch_won_feed(registry, user_id, okpd_codes, stop_words)
        elif feed_type == 'commission':
            return self._fetch_commission_feed(registry, user_id, okpd_codes, stop_words)
        else:
            return []