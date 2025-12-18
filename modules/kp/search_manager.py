"""
Менеджер поиска товаров с дебаунсингом и кэшированием
"""

from typing import Optional, Dict, Any, List, Callable
from PyQt5.QtCore import QTimer
from loguru import logger
from services.fuzzy_search import fuzzy_search_products, combine_search_results


class SearchManager:
    """Управление поиском товаров с дебаунсингом"""
    
    def __init__(
        self,
        product_repo,
        search_callback: Callable[[List[Dict[str, Any]]], None],
        debounce_ms: int = 300
    ):
        """
        Args:
            product_repo: Репозиторий товаров
            search_callback: Функция для отображения результатов
            debounce_ms: Задержка дебаунсинга в миллисекундах
        """
        self.product_repo = product_repo
        self.search_callback = search_callback
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._execute_search)
        self.debounce_ms = debounce_ms
        self._last_params = {}
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
    
    def search(
        self,
        category_id: Optional[int] = None,
        subcategory_id: Optional[int] = None,
        manufacturer_id: Optional[int] = None,
        search_text: Optional[str] = None
    ) -> None:
        """
        Запуск поиска с дебаунсингом
        
        Args:
            category_id: ID категории
            subcategory_id: ID подкатегории
            manufacturer_id: ID производителя
            search_text: Текст для поиска
        """
        # Останавливаем предыдущий таймер
        self.debounce_timer.stop()
        
        # Сохраняем параметры
        self._last_params = {
            'category_id': category_id,
            'subcategory_id': subcategory_id,
            'manufacturer_id': manufacturer_id,
            'search_text': search_text
        }
        
        # Запускаем таймер
        self.debounce_timer.start(self.debounce_ms)
    
    def _execute_search(self) -> None:
        """Выполнение поиска"""
        if not self.product_repo:
            logger.warning("Репозиторий товаров не инициализирован")
            return
        
        try:
            params = self._last_params
            category_id = params.get('category_id')
            subcategory_id = params.get('subcategory_id')
            manufacturer_id = params.get('manufacturer_id')
            search_text = params.get('search_text')
            
            # Проверяем кэш
            cache_key = self._build_cache_key(category_id, subcategory_id, manufacturer_id, search_text)
            if cache_key in self._cache:
                logger.debug(f"Использован кэш для поиска: {cache_key}")
                self.search_callback(self._cache[cache_key])
                return
            
            # Выполняем поиск в БД
            products = self.product_repo.search_products(
                category_id=category_id,
                subcategory_id=subcategory_id,
                manufacturer_id=manufacturer_id,
                search_text=None,  # Не используем текстовый поиск в БД
                limit=1000
            )
            
            # Применяем текстовый поиск если есть
            if search_text and len(search_text) >= 2:
                exact_matches = [
                    p for p in products 
                    if search_text.lower() in p.get('name', '').lower()
                ]
                
                fuzzy_matches = fuzzy_search_products(
                    products,
                    search_text,
                    threshold=70,
                    limit=100
                )
                
                products = combine_search_results(exact_matches, fuzzy_matches, limit=200)
                logger.debug(f"Точных совпадений: {len(exact_matches)}, нечетких: {len(fuzzy_matches)}")
            elif search_text:
                products = [
                    p for p in products 
                    if search_text.lower() in p.get('name', '').lower()
                ]
            
            # Сохраняем в кэш
            self._cache[cache_key] = products
            # Ограничиваем размер кэша
            if len(self._cache) > 50:
                # Удаляем самый старый ключ
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            # Отображаем результаты
            self.search_callback(products)
            logger.info(f"Найдено товаров: {len(products)}")
        except Exception as e:
            logger.error(f"Ошибка при поиске товаров: {e}")
            self.search_callback([])
    
    def _build_cache_key(
        self,
        category_id: Optional[int],
        subcategory_id: Optional[int],
        manufacturer_id: Optional[int],
        search_text: Optional[str]
    ) -> str:
        """Построение ключа кэша"""
        return f"{category_id}_{subcategory_id}_{manufacturer_id}_{search_text or ''}"
    
    def clear_cache(self) -> None:
        """Очистка кэша"""
        self._cache.clear()
        logger.debug("Кэш поиска очищен")

