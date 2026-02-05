"""
MODULE: scripts.check_db_schema
RESPONSIBILITY: Checking database schema for product_catalog_2.
ALLOWED: sys, os, core.dependency_injection, loguru.
FORBIDDEN: None.
ERRORS: None.

Скрипт для проверки схемы БД product_catalog_2
"""
import sys
import os
sys.path.insert(0, os.getcwd())

from core.dependency_injection import DependencyContainer
from loguru import logger

def main():
    logger.info("=" * 80)
    logger.info("ПРОВЕРКА СХЕМЫ БД product_catalog_2")
    logger.info("=" * 80)
    
    # Инициализация
    container = DependencyContainer()
    db_manager = container.get_commercial_database_manager()
    
    # Получаем список таблиц
    query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """
    
    logger.info("Получение списка таблиц...")
    tables = db_manager.execute_query(query)
    
    logger.info(f"\nНайдено таблиц: {len(tables)}")
    logger.info("-" * 80)
    
    for row in tables:
        table_name = row.get("table_name")
        logger.info(f"  - {table_name}")
    
    logger.info("-" * 80)
    
    # Проверяем наличие таблицы products
    if any(row.get("table_name") == "products" for row in tables):
        logger.success("✅ Таблица 'products' найдена!")
        
        # Получаем структуру таблицы products
        columns_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'products' AND table_schema = 'public'
            ORDER BY ordinal_position
        """
        columns = db_manager.execute_query(columns_query)
        logger.info(f"\nСтруктура таблицы 'products' ({len(columns)} колонок):")
        for col in columns:
            logger.info(f"  - {col.get('column_name')}: {col.get('data_type')}")
            
        # Считаем количество записей
        count_query = "SELECT COUNT(*) as cnt FROM products"
        count_result = db_manager.execute_query(count_query)
        count = count_result[0].get("cnt", 0) if count_result else 0
        logger.info(f"\nКоличество записей в 'products': {count}")
        
    else:
        logger.warning("⚠️ Таблица 'products' НЕ найдена!")
        logger.info("\nИщем похожие таблицы (prod*, item*, товар*, nomenclature*)...")
        
        for row in tables:
            table_name = row.get("table_name", "").lower()
            if any(keyword in table_name for keyword in ["prod", "item", "товар", "nomenclature", "catalog"]):
                logger.info(f"  📦 Возможная таблица: {row.get('table_name')}")

if __name__ == "__main__":
    main()
