"""
Модуль для управления кэшем параметров поиска в виджете закупок

Содержит методы для восстановления параметров из кэша
"""

from typing import Optional
from loguru import logger

from modules.bids.search_params_cache import SearchParamsCache


class BidsCacheManager:
    """
    Класс для управления кэшем параметров поиска
    
    Инкапсулирует логику восстановления параметров из кэша
    """
    
    def __init__(self, search_params_cache: SearchParamsCache):
        """
        Инициализация менеджера кэша
        
        Args:
            search_params_cache: Экземпляр SearchParamsCache для работы с кэшем
        """
        self.search_params_cache = search_params_cache
    
    def restore_region_from_cache(self, region_combo) -> None:
        """
        Восстановление выбранного региона из кэша
        
        Args:
            region_combo: QComboBox с регионами
        """
        if not region_combo:
            return
        
        cached_region_id = self.search_params_cache.get_region_id()
        if cached_region_id is None:
            return
        
        for i in range(region_combo.count()):
            region_data = region_combo.itemData(i)
            if region_data and region_data.get('id') == cached_region_id:
                region_combo.setCurrentIndex(i)
                logger.info(f"Восстановлен регион из кэша: {cached_region_id}")
                return
    
    def restore_category_from_cache(self, category_filter_combo) -> None:
        """
        Восстановление выбранной категории из кэша
        
        Args:
            category_filter_combo: QComboBox с категориями
        """
        if not category_filter_combo:
            return
        
        cached_category_id = self.search_params_cache.get_category_id()
        if cached_category_id is None:
            return
        
        for i in range(category_filter_combo.count()):
            category_id = category_filter_combo.itemData(i)
            if category_id == cached_category_id:
                category_filter_combo.setCurrentIndex(i)
                logger.info(f"Восстановлена категория из кэша: {cached_category_id}")
                return
    
    def restore_okpd_search_from_cache(self, okpd_search_input) -> None:
        """
        Восстановление текста поиска ОКПД из кэша
        
        Args:
            okpd_search_input: QLineEdit для поиска ОКПД
        """
        if not okpd_search_input:
            return
        
        cached_search_text = self.search_params_cache.get_okpd_search_text()
        if cached_search_text:
            okpd_search_input.setText(cached_search_text)
            logger.debug(f"Восстановлен текст поиска ОКПД из кэша: {cached_search_text}")
    
    def restore_all_search_params_from_cache(
        self,
        region_combo=None,
        category_filter_combo=None,
        okpd_search_input=None
    ) -> None:
        """
        Восстановление всех параметров поиска из кэша
        
        Args:
            region_combo: QComboBox с регионами (опционально)
            category_filter_combo: QComboBox с категориями (опционально)
            okpd_search_input: QLineEdit для поиска ОКПД (опционально)
        """
        logger.info("Восстановление параметров поиска из кэша...")
        
        if region_combo:
            self.restore_region_from_cache(region_combo)
        if category_filter_combo:
            self.restore_category_from_cache(category_filter_combo)
        if okpd_search_input:
            self.restore_okpd_search_from_cache(okpd_search_input)
        
        logger.info("Параметры поиска восстановлены из кэша")

