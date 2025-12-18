"""
Сервис для подсчета количества закупок

Отвечает за получение количества закупок различных типов
с учетом фильтров пользователя.
"""

from typing import Dict, Optional, List
from loguru import logger
from psycopg2.extras import RealDictCursor

from services.tender_repository import TenderRepository
from services.tender_repositories.feeds.feed_filters import FeedFilters, WonFilters


class PurchasesCountsService:
    """
    Сервис для подсчета количества закупок
    
    Используется для обновления счетчиков в подменю закупок.
    """
    
    def __init__(self, tender_repo: TenderRepository, user_id: int):
        """
        Инициализация сервиса
        
        Args:
            tender_repo: Репозиторий закупок
            user_id: ID пользователя
        """
        self.tender_repo = tender_repo
        self.user_id = user_id
    
    def get_counts(self, category_id: Optional[int] = None, user_okpd_codes: Optional[list] = None, user_stop_words: Optional[list] = None, region_id: Optional[int] = None) -> Dict[str, int]:
        """
        Получение количества закупок всех типов по статусам
        
        Args:
            category_id: ID категории для фильтрации (опционально)
            user_okpd_codes: Список ОКПД кодов пользователя (если уже получены)
            user_stop_words: Список стоп-слов пользователя (если уже получены)
            region_id: ID региона для фильтрации (опционально, если None - все регионы)
        
        Returns:
            Словарь с количеством закупок:
            {
                'purchases_44fz_new': int,  # Новые закупки 44ФЗ
                'purchases_44fz_won': int,  # Разыгранные закупки 44ФЗ
                'purchases_44fz_commission': int,  # Работа комиссии 44 ФЗ
                'purchases_223fz_new': int,  # Новые закупки 223ФЗ
                'purchases_223fz_won': int,  # Разыгранные закупки 223ФЗ
            }
        """
        counts = {}
        
        # Получаем фильтры пользователя, если не переданы
        if user_okpd_codes is None:
            try:
                # Если указана категория, получаем ОКПД коды из категории
                if category_id is not None:
                    user_okpd_codes = self.tender_repo.get_okpd_codes_by_category(self.user_id, category_id)
                else:
                    # Иначе получаем все ОКПД коды пользователя
                    user_okpd_list = self.tender_repo.get_user_okpd_codes(self.user_id)
                    if user_okpd_list:
                        user_okpd_codes = [item.get('okpd_code') for item in user_okpd_list if item.get('okpd_code')]
            except Exception as e:
                logger.warning(f"Ошибка получения ОКПД кодов пользователя: {e}")
                user_okpd_codes = []
        
        if user_stop_words is None:
            user_stop_words = None
            try:
                # Получаем стоп-слова пользователя
                user_stop_words_list = self.tender_repo.get_user_stop_words(self.user_id)
                if user_stop_words_list:
                    user_stop_words = [item.get('stop_word') for item in user_stop_words_list if item.get('stop_word')]
            except Exception as e:
                logger.warning(f"Ошибка получения стоп-слов пользователя: {e}")
        
        # region_id передается как параметр, если None - все регионы
        
        okpd_ids = self._resolve_okpd_ids(user_okpd_codes) if user_okpd_codes else []
        
        counts['purchases_44fz_new'] = self._count_tenders(
            "reestr_contract_44_fz", "r.status_id = 1", okpd_ids, region_id, user_stop_words, "новых закупок 44ФЗ"
        )
        counts['purchases_223fz_new'] = self._count_tenders(
            "reestr_contract_223_fz", "(r.status_id IS NULL OR r.status_id != 4)", okpd_ids, region_id, user_stop_words, "новых закупок 223ФЗ"
        )
        counts['purchases_44fz_won'] = self._count_tenders(
            "reestr_contract_44_fz", "r.status_id = 3", okpd_ids, region_id, user_stop_words, "разыгранных закупок 44ФЗ"
        )
        counts['purchases_223fz_won'] = self._count_won_223fz(okpd_ids, region_id, user_stop_words)
        counts['purchases_44fz_commission'] = self._count_tenders(
            "reestr_contract_44_fz", "r.status_id = 2", okpd_ids, region_id, user_stop_words, "работы комиссии 44ФЗ"
        )
        
        return counts
    
    def _count_tenders(
        self,
        table_name: str,
        status_condition: str,
        okpd_ids: list,
        region_id: Optional[int],
        user_stop_words: Optional[List[str]],
        error_context: str
    ) -> int:
        """Подсчет количества торгов по заданным условиям"""
        if not okpd_ids:
            return 0
        
        try:
            placeholders = ",".join(["%s"] * len(okpd_ids))
            query = f"""
                SELECT COUNT(DISTINCT r.id) as total_count 
                FROM {table_name} r
                WHERE {status_condition}
                  AND r.okpd_id IN ({placeholders})
            """
            params = list(okpd_ids)
            query, params = self._add_filters(query, params, region_id, user_stop_words)
            
            result = self.tender_repo.db_manager.execute_query(query, tuple(params), RealDictCursor)
            return result[0].get("total_count", 0) if result else 0
        except Exception as e:
            logger.error(f"Ошибка подсчета {error_context}: {e}")
            return 0
    
    def _count_won_223fz(
        self,
        okpd_ids: list,
        region_id: Optional[int],
        user_stop_words: Optional[List[str]]
    ) -> int:
        """Подсчет разыгранных закупок 223ФЗ (через даты)"""
        if not okpd_ids:
            return 0
        
        try:
            from datetime import date, timedelta
            today = date.today()
            min_delivery_date = today + timedelta(days=90)
            placeholders = ",".join(["%s"] * len(okpd_ids))
            query = f"""
                SELECT COUNT(DISTINCT r.id) as total_count 
                FROM reestr_contract_223_fz r
                WHERE r.end_date < %s
                  AND r.delivery_end_date IS NOT NULL 
                  AND r.delivery_end_date >= %s
                  AND (r.status_id IS NULL OR r.status_id != 4)
                  AND r.okpd_id IN ({placeholders})
            """
            params = [today, min_delivery_date] + list(okpd_ids)
            query, params = self._add_filters(query, params, region_id, user_stop_words)
            
            result = self.tender_repo.db_manager.execute_query(query, tuple(params), RealDictCursor)
            return result[0].get("total_count", 0) if result else 0
        except Exception as e:
            logger.error(f"Ошибка подсчета разыгранных закупок 223ФЗ: {e}")
            return 0
    
    @staticmethod
    def _add_filters(
        query: str,
        params: list,
        region_id: Optional[int],
        user_stop_words: Optional[List[str]]
    ) -> tuple:
        """Добавление фильтров по региону и стоп-словам к запросу"""
        if region_id:
            query += " AND r.region_id = %s"
            params.append(region_id)
        if user_stop_words:
            for stop_word in user_stop_words:
                query += " AND LOWER(r.auction_name) NOT LIKE %s"
                params.append(f"%{stop_word.lower()}%")
        return query, params
    
    def _resolve_okpd_ids(self, user_okpd_codes: list) -> list:
        """Преобразование ОКПД кодов в ID для использования в запросах"""
        if not user_okpd_codes:
            return []
        try:
            query = """
                SELECT DISTINCT id FROM collection_codes_okpd
                WHERE main_code = ANY(%s) OR sub_code = ANY(%s)
            """
            results = self.tender_repo.db_manager.execute_query(
                query,
                (user_okpd_codes, user_okpd_codes),
                RealDictCursor
            )
            return [row["id"] for row in results if row.get("id")] if results else []
        except Exception as e:
            logger.error(f"Ошибка преобразования ОКПД кодов в ID: {e}")
            return []

