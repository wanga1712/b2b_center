"""
Репозиторий для работы с товарами из базы данных

Предоставляет методы для получения товаров, категорий, производителей,
цен и информации об упаковке с учетом всех связей между таблицами.
"""

from typing import List, Optional, Dict, Any
from core.database import DatabaseManager
from core.models import (
    Product, ProductPricing, ProductPackaging,
    Category, Subcategory, Manufacturer
)
from loguru import logger


class ProductRepository:
    """
    Репозиторий для работы с товарами и связанными сущностями
    
    Предоставляет методы для:
    - Поиска товаров по различным критериям
    - Получения категорий, подкатегорий, производителей
    - Получения цен и информации об упаковке
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Инициализация репозитория
        
        Args:
            db_manager: Менеджер базы данных
        """
        self.db = db_manager

    def get_categories(self) -> List[Dict[str, Any]]:
        """
        Получение списка всех категорий
        
        Returns:
            Список словарей с полями id и name
        """
        try:
            query = "SELECT id, name FROM categories ORDER BY name"
            return self.db.execute_query(query)
        except Exception as e:
            logger.error(f"Ошибка при получении категорий: {e}")
            return []

    def get_subcategories(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получение списка подкатегорий
        
        Args:
            category_id: Идентификатор категории (опционально)
        
        Returns:
            Список словарей с полями id, name, category_id
        """
        try:
            if category_id:
                query = """
                    SELECT id, name, category_id 
                    FROM subcategories 
                    WHERE category_id = %s 
                    ORDER BY name
                """
                return self.db.execute_query(query, (category_id,))
            else:
                query = "SELECT id, name, category_id FROM subcategories ORDER BY name"
                return self.db.execute_query(query)
        except Exception as e:
            logger.error(f"Ошибка при получении подкатегорий: {e}")
            return []

    def get_manufacturers(self) -> List[Dict[str, Any]]:
        """
        Получение списка всех производителей
        
        Returns:
            Список словарей с полями id и name
        """
        try:
            query = "SELECT id, name FROM manufacturers ORDER BY name"
            return self.db.execute_query(query)
        except Exception as e:
            logger.error(f"Ошибка при получении производителей: {e}")
            return []

    def search_products(
        self,
        category_id: Optional[int] = None,
        subcategory_id: Optional[int] = None,
        manufacturer_id: Optional[int] = None,
        search_text: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Поиск товаров по различным критериям
        
        Args:
            category_id: Идентификатор категории
            subcategory_id: Идентификатор подкатегории
            manufacturer_id: Идентификатор производителя
            search_text: Текст для поиска по названию товара
            limit: Максимальное количество результатов
        
        Returns:
            Список товаров с полной информацией включая категорию, производителя и цену
        """
        try:
            query = """
                SELECT 
                    p.id,
                    p.name,
                    p.description,
                    p.technical_specs,
                    p.application_areas,
                    p.advantages,
                    p.consumption,
                    p.storage,
                    p.color,
                    p.safety,
                    c.name as category_name,
                    s.name as subcategory_name,
                    m.name as manufacturer_name,
                    m.id as manufacturer_id,
                    pp.id as pricing_id,
                    pp.kit_name,
                    pp.container_type,
                    pp.size,
                    pp.weight,
                    pp.price,
                    pp.additional_info
                FROM products p
                LEFT JOIN subcategories s ON p.subcategory_id = s.id
                LEFT JOIN categories c ON s.category_id = c.id
                LEFT JOIN manufacturers m ON p.manufacturer_id = m.id
                LEFT JOIN product_pricing pp ON p.id = pp.product_id
                WHERE 1=1
            """
            params = []

            if category_id:
                query += " AND c.id = %s"
                params.append(category_id)

            if subcategory_id:
                query += " AND s.id = %s"
                params.append(subcategory_id)

            if manufacturer_id:
                query += " AND m.id = %s"
                params.append(manufacturer_id)

            if search_text:
                query += " AND p.name ILIKE %s"
                params.append(f"%{search_text}%")

            query += " ORDER BY p.name LIMIT %s"
            params.append(limit)

            return self.db.execute_query(query, tuple(params))
        except Exception as e:
            logger.error(f"Ошибка при поиске товаров: {e}")
            return []

    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение полной информации о товаре по идентификатору
        
        Args:
            product_id: Идентификатор товара
        
        Returns:
            Словарь с полной информацией о товаре или None
        """
        try:
            query = """
                SELECT 
                    p.*,
                    c.name as category_name,
                    s.name as subcategory_name,
                    m.name as manufacturer_name
                FROM products p
                LEFT JOIN subcategories s ON p.subcategory_id = s.id
                LEFT JOIN categories c ON s.category_id = c.id
                LEFT JOIN manufacturers m ON p.manufacturer_id = m.id
                WHERE p.id = %s
            """
            results = self.db.execute_query(query, (product_id,))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Ошибка при получении товара {product_id}: {e}")
            return None

    def get_product_pricing(self, product_id: int) -> List[Dict[str, Any]]:
        """
        Получение всех вариантов цен для товара
        
        Args:
            product_id: Идентификатор товара
        
        Returns:
            Список вариантов цен с информацией об упаковке
        """
        try:
            query = """
                SELECT 
                    pp.*,
                    ppkg.quantity_per_pallet
                FROM product_pricing pp
                LEFT JOIN product_packaging ppkg ON pp.product_id = ppkg.product_id 
                    AND pp.kit_name = ppkg.kit_name
                WHERE pp.product_id = %s
                ORDER BY pp.weight
            """
            return self.db.execute_query(query, (product_id,))
        except Exception as e:
            logger.error(f"Ошибка при получении цен для товара {product_id}: {e}")
            return []

    def get_product_packaging(self, product_id: int, kit_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получение информации об упаковке товара
        
        Args:
            product_id: Идентификатор товара
            kit_name: Название комплекта (опционально)
        
        Returns:
            Список информации об упаковке
        """
        try:
            if kit_name:
                query = """
                    SELECT * FROM product_packaging 
                    WHERE product_id = %s AND kit_name = %s
                """
                return self.db.execute_query(query, (product_id, kit_name))
            else:
                query = "SELECT * FROM product_packaging WHERE product_id = %s"
                return self.db.execute_query(query, (product_id,))
        except Exception as e:
            logger.error(f"Ошибка при получении упаковки для товара {product_id}: {e}")
            return []

    def update_product_weight(self, pricing_id: int, weight: float) -> bool:
        """
        Обновление веса товара в таблице product_pricing
        
        Args:
            pricing_id: Идентификатор записи о цене
            weight: Новый вес (кг)
        
        Returns:
            True если обновление успешно, False в противном случае
        """
        try:
            query = """
                UPDATE product_pricing 
                SET weight = %s 
                WHERE id = %s
            """
            self.db.execute_query(query, (weight, pricing_id))
            logger.info(f"Обновлен вес для pricing_id={pricing_id}, новый вес={weight} кг")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении веса для pricing_id={pricing_id}: {e}")
            return False

    def update_product_price(self, pricing_id: int, price: float) -> bool:
        """
        Обновление цены товара в таблице product_pricing
        
        Args:
            pricing_id: Идентификатор записи о цене
            price: Новая цена
        
        Returns:
            True если обновление успешно, False в противном случае
        """
        try:
            query = """
                UPDATE product_pricing 
                SET price = %s 
                WHERE id = %s
            """
            self.db.execute_query(query, (price, pricing_id))
            logger.info(f"Обновлена цена для pricing_id={pricing_id}, новая цена={price}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении цены для pricing_id={pricing_id}: {e}")
            return False

    def update_product_name(self, product_id: int, name: str) -> bool:
        """
        Обновление наименования товара в таблице products
        
        Args:
            product_id: Идентификатор товара
            name: Новое наименование
        
        Returns:
            True если обновление успешно, False в противном случае
        """
        try:
            query = """
                UPDATE products 
                SET name = %s 
                WHERE id = %s
            """
            self.db.execute_query(query, (name, product_id))
            logger.info(f"Обновлено наименование для product_id={product_id}, новое наименование={name}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении наименования для product_id={product_id}: {e}")
            return False

    def update_product_unit(self, pricing_id: int, container_type: str, size: str) -> bool:
        """
        Обновление единицы измерения товара в таблице product_pricing
        
        Args:
            pricing_id: Идентификатор записи о цене
            container_type: Тип тары (мешок, бочка и т.д.)
            size: Размер упаковки
        
        Returns:
            True если обновление успешно, False в противном случае
        """
        try:
            query = """
                UPDATE product_pricing 
                SET container_type = %s, size = %s
                WHERE id = %s
            """
            self.db.execute_query(query, (container_type, size, pricing_id))
            logger.info(f"Обновлена единица измерения для pricing_id={pricing_id}, container_type={container_type}, size={size}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении единицы измерения для pricing_id={pricing_id}: {e}")
            return False

