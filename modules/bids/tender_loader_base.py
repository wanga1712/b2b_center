"""
Базовые методы для загрузки тендеров.
"""

from typing import Optional, Dict, Any, List
from loguru import logger

from services.tender_repository import TenderRepository


class TenderLoaderBase:
    """Базовый класс с общими методами для загрузки тендеров"""
    
    def __init__(self, tender_repo: TenderRepository):
        """
        Инициализация базового загрузчика
        
        Args:
            tender_repo: Репозиторий для работы с тендерами
        """
        self.tender_repo = tender_repo
    
    def _get_user_filters(self, user_id: int, category_filter_combo=None, cache=None) -> Dict[str, Any]:
        """
        Получение фильтров пользователя
        
        Args:
            user_id: ID пользователя
            category_filter_combo: ComboBox с категориями (опционально)
            cache: Кэш параметров поиска для получения region_id (опционально)
        
        Returns:
            Словарь с фильтрами: category_id, user_okpd_codes, user_stop_words, region_id
        """
        category_id = None
        # Сначала пробуем получить из комбобокса
        if category_filter_combo:
            category_id = category_filter_combo.currentData()
            logger.debug(f"Категория получена из комбобокса: {category_id}")
        # Если не получили из комбобокса, пробуем из кэша
        if category_id is None and cache:
            category_id = cache.get_category_id()
            if category_id:
                logger.info(f"Категория получена из кэша: {category_id}")
            else:
                logger.warning(f"Категория не найдена в кэше (cache={cache}, get_category_id()={cache.get_category_id()})")
        elif category_id is None and not cache:
            logger.warning("Кэш не передан в _get_user_filters")
        
        user_okpd_codes = None
        if category_id is None:
            # Если категория не выбрана - НЕ загружаем закупки
            # Пользователь должен выбрать категорию для фильтрации
            logger.warning(f"Категория не выбрана для пользователя {user_id} - закупки не будут загружены")
            user_okpd_codes = []  # Пустой список - закупки не будут загружены
        else:
            # Если выбрана категория, получаем ОКПД коды ТОЛЬКО из этой категории
            user_okpd_codes = self.tender_repo.get_okpd_codes_by_category(user_id, category_id)
            logger.info(f"Используются ОКПД коды из категории {category_id}: {len(user_okpd_codes)} кодов")
        
        # Получаем стоп-слова только если они есть
        user_stop_words_data = self.tender_repo.get_user_stop_words(user_id)
        user_stop_words = [sw.get('stop_word', '') for sw in user_stop_words_data if sw.get('stop_word')] if user_stop_words_data else []
        if user_stop_words:
            logger.info(f"Используются стоп-слова: {len(user_stop_words)} слов")
        else:
            logger.info("Стоп-слова не используются (список пуст)")
        
        # Получаем region_id из кэша, если доступен
        region_id = None
        if cache:
            region_id = cache.get_region_id()
        
        return {
            'category_id': category_id,
            'user_okpd_codes': user_okpd_codes,
            'user_stop_words': user_stop_words,
            'region_id': region_id,
        }
    
    def _process_tenders_result(self, tenders: List[Dict[str, Any]]) -> tuple:
        """
        Обработка результата загрузки тендеров
        
        Args:
            tenders: Список тендеров
        
        Returns:
            Кортеж (tenders, total_count)
        """
        total_count = None
        if tenders and '_total_count' in tenders[0]:
            total_count = tenders[0].pop('_total_count', len(tenders))
            tenders[0].pop('_loaded_count', None)
        return tenders, total_count

