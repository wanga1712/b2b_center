"""
Тест декомпозиции ProductRepository.

Проверяет, что все сервисы создаются корректно и предоставляют
полный интерфейс оригинального ProductRepository.
"""

import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_service_creation():
    """Тестирует создание экземпляров всех сервисов."""
    print("🧪 Тестируем создание экземпляров сервисов...")
    
    try:
        # Импортируем все сервисы
        from services.product_services.category_service import CategoryService
        from services.product_services.manufacturer_service import ManufacturerService
        from services.product_services.product_search_service import ProductSearchService
        from services.product_services.pricing_service import PricingService
        from services.product_services.packaging_service import PackagingService
        from services.product_services.product_coordinator import ProductCoordinator
        from services.product_services.product_repository_facade import ProductRepositoryFacade
        
        # Имитируем db_manager для тестов
        class MockDBManager:
            def execute_query(self, query, params=None):
                return []
        
        db_manager = MockDBManager()
        
        # Создаем все сервисы
        services = [
            CategoryService(db_manager),
            ManufacturerService(db_manager),
            ProductSearchService(db_manager),
            PricingService(db_manager),
            PackagingService(db_manager),
            ProductCoordinator(db_manager),
            ProductRepositoryFacade(db_manager)
        ]
        
        print(f"✅ Все сервисы успешно созданы!")
        print(f"   Создано {len(services)} сервисов")
        
        # Проверяем, что фасад имеет все необходимые методы
        facade = ProductRepositoryFacade(db_manager)
        required_methods = [
            'get_categories', 'get_subcategories', 'clear_categories_cache',
            'clear_subcategories_cache', 'get_manufacturers', 'clear_manufacturers_cache',
            'clear_all_cache', 'search_products', 'get_product_by_id', 'get_product_pricing',
            'update_product_weight', 'update_product_price', 'update_product_unit',
            'get_product_packaging', 'update_product_name'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(facade, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Отсутствуют методы в фасаде: {missing_methods}")
            return False
        
        print("✅ Фасад имеет все необходимые методы!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания сервисов: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_method_signatures():
    """Тестирует сигнатуры методов фасада."""
    print("🧪 Тестируем сигнатуры методов фасада...")
    
    try:
        from services.product_services.product_repository_facade import ProductRepositoryFacade
        from inspect import signature
        
        class MockDBManager:
            def execute_query(self, query, params=None):
                return []
        
        db_manager = MockDBManager()
        facade = ProductRepositoryFacade(db_manager)
        
        # Проверяем несколько ключевых методов
        methods_to_check = [
            ('get_categories', 1),          # 1 параметр (без self)
            ('get_subcategories', 2),       # 2 параметра (без self)
            ('get_manufacturers', 1),       # 1 параметр (без self)
            ('search_products', 5),         # 5 параметров (без self)
            ('get_product_by_id', 1),       # 1 параметр (без self)
        ]
        
        for method_name, expected_params in methods_to_check:
            method = getattr(facade, method_name)
            sig = signature(method)
            actual_params = len(sig.parameters)
            
            if actual_params == expected_params:
                print(f"✅ Метод {method_name} - OK ({actual_params} параметров)")
            else:
                print(f"❌ Метод {method_name} имеет {actual_params} параметров, ожидалось {expected_params}")
                return False
        
        print("✅ Все сигнатуры методов корректны!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки сигнатур: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция тестирования."""
    print("🚀 Запуск тестов декомпозиции ProductRepository")
    print("=" * 60)
    
    tests = [
        test_service_creation,
        test_method_signatures
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Результаты тестирования:")
    print(f"✅ Пройдено: {passed}/{len(tests)}")
    print(f"❌ Провалено: {failed}/{len(tests)}")
    
    if failed == 0:
        print("🎉 Все тесты пройдены успешно! Декомпозиция завершена.")
        return True
    else:
        print("⚠️  Некоторые тесты провалились. Требуется доработка.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)