"""
Модуль для кэширования параметров поиска закупок.

Сохраняет параметры поиска (категория, регион) в памяти,
чтобы восстановить их после переподключения к БД.
Также кэширует загруженные закупки для быстрого отображения.
"""

from typing import Optional, Dict, Any, List, Tuple
from loguru import logger
import hashlib


class SearchParamsCache:
    """Кэш для параметров поиска закупок и самих закупок"""
    
    def __init__(self):
        """Инициализация кэша"""
        self._category_id: Optional[int] = None
        self._region_id: Optional[int] = None
        self._region_data: Optional[Dict[str, Any]] = None
        self._okpd_search_text: Optional[str] = None
        
        # Кэш закупок: ключ = (registry_type, tender_type, user_id, filters_hash)
        # значение = {'tenders': List[Dict], 'total_count': int, 'filters': Dict}
        self._tenders_cache: Dict[Tuple[str, str, int, str], Dict[str, Any]] = {}
    
    def save_category(self, category_id: Optional[int]) -> None:
        """Сохранение выбранной категории"""
        self._category_id = category_id
        logger.debug(f"Сохранена категория в кэш: {category_id}")
    
    def save_region(self, region_id: Optional[int], region_data: Optional[Dict[str, Any]] = None) -> None:
        """Сохранение выбранного региона"""
        self._region_id = region_id
        self._region_data = region_data
        logger.debug(f"Сохранен регион в кэш: {region_id}")
    
    def save_okpd_search_text(self, search_text: Optional[str]) -> None:
        """Сохранение текста поиска ОКПД"""
        self._okpd_search_text = search_text
        logger.debug(f"Сохранен текст поиска ОКПД в кэш: {search_text}")
    
    def get_category_id(self) -> Optional[int]:
        """Получение сохраненной категории"""
        return self._category_id
    
    def get_region_id(self) -> Optional[int]:
        """Получение сохраненного региона"""
        return self._region_id
    
    def get_region_data(self) -> Optional[Dict[str, Any]]:
        """Получение данных сохраненного региона"""
        return self._region_data
    
    def get_okpd_search_text(self) -> Optional[str]:
        """Получение сохраненного текста поиска ОКПД"""
        return self._okpd_search_text
    
    def clear(self) -> None:
        """Очистка кэша"""
        self._category_id = None
        self._region_id = None
        self._region_data = None
        self._okpd_search_text = None
        logger.debug("Кэш параметров поиска очищен")
    
    def has_cached_params(self) -> bool:
        """Проверка наличия сохраненных параметров"""
        return (
            self._category_id is not None or
            self._region_id is not None or
            self._okpd_search_text is not None
        )
    
    def _get_filters_hash(self, filters: Dict[str, Any]) -> str:
        """
        Генерирует хэш фильтров для использования в качестве ключа кэша.
        
        Args:
            filters: Словарь с фильтрами (user_okpd_codes, user_stop_words, region_id, category_id)
            
        Returns:
            Строка хэша
        """
        # Сортируем списки для консистентности
        okpd_codes = sorted(filters.get('user_okpd_codes', []) or [])
        stop_words = sorted(filters.get('user_stop_words', []) or [])
        region_id = filters.get('region_id')
        category_id = filters.get('category_id')
        
        # Создаем строку для хэширования
        hash_string = f"{okpd_codes}|{stop_words}|{region_id}|{category_id}"
        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()
    
    def save_tenders(
        self,
        registry_type: str,
        tender_type: str,
        user_id: int,
        filters: Dict[str, Any],
        tenders: List[Dict[str, Any]],
        total_count: Optional[int] = None
    ) -> None:
        """
        Сохранение закупок в кэш.
        
        Args:
            registry_type: Тип реестра ('44fz' или '223fz')
            tender_type: Тип торгов ('new' для новых, 'won' для разыгранных)
            user_id: ID пользователя
            filters: Словарь с фильтрами (user_okpd_codes, user_stop_words, region_id, category_id)
            tenders: Список закупок
            total_count: Общее количество закупок в БД
        """
        filters_hash = self._get_filters_hash(filters)
        cache_key = (registry_type, tender_type, user_id, filters_hash)
        
        self._tenders_cache[cache_key] = {
            'tenders': tenders,
            'total_count': total_count,
            'filters': filters.copy(),
        }
        
        logger.debug(
            f"Сохранено в кэш: {len(tenders)} закупок "
            f"({registry_type}, {tender_type}, user_id={user_id})"
        )
    
    def get_tenders(
        self,
        registry_type: str,
        tender_type: str,
        user_id: int,
        filters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Получение закупок из кэша.
        
        Args:
            registry_type: Тип реестра ('44fz' или '223fz')
            tender_type: Тип торгов ('new' для новых, 'won' для разыгранных)
            user_id: ID пользователя
            filters: Словарь с фильтрами (user_okpd_codes, user_stop_words, region_id, category_id)
            
        Returns:
            Словарь с ключами 'tenders' и 'total_count', или None если нет в кэше
        """
        filters_hash = self._get_filters_hash(filters)
        cache_key = (registry_type, tender_type, user_id, filters_hash)
        
        cached = self._tenders_cache.get(cache_key)
        if cached:
            logger.debug(
                f"Найдено в кэше: {len(cached['tenders'])} закупок "
                f"({registry_type}, {tender_type}, user_id={user_id})"
            )
            return cached
        
        logger.debug(f"Не найдено в кэше ({registry_type}, {tender_type}, user_id={user_id})")
        return None
    
    def clear_tenders_cache(self, registry_type: Optional[str] = None, tender_type: Optional[str] = None) -> None:
        """
        Очистка кэша закупок.
        
        Args:
            registry_type: Если указан, очищает только для этого реестра (None - все)
            tender_type: Если указан, очищает только для этого типа (None - все)
        """
        if registry_type is None and tender_type is None:
            # Очищаем весь кэш
            self._tenders_cache.clear()
            logger.debug("Кэш закупок полностью очищен")
        else:
            # Очищаем только соответствующие записи
            keys_to_remove = []
            for key in self._tenders_cache.keys():
                reg_type, ten_type, _, _ = key
                if (registry_type is None or reg_type == registry_type) and \
                   (tender_type is None or ten_type == tender_type):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._tenders_cache[key]
            
            logger.debug(f"Очищено записей из кэша: {len(keys_to_remove)}")

