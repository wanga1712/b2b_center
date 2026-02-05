"""
Тест декомпозиции TenderMatchRepository.

Проверяет, что все сервисы созданы корректно и фасад работает.
"""

import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_service_imports():
    """Тестирует импорт всех созданных сервисов."""
    print("🧪 Тестируем импорт сервисов...")
    
    try:
        from services.match_services.match_result_service import MatchResultService
        from services.match_services.match_query_service import MatchQueryService
        from services.match_services.match_status_service import MatchStatusService
        from services.match_services.tender_lock_service import TenderLockService
        from services.match_services.match_detail_service import MatchDetailService
        from services.match_services.file_error_service import FileErrorService
        from services.match_services.match_coordinator import MatchCoordinator
        from services.match_services.tender_match_repository_facade import TenderMatchRepositoryFacade
        
        print("✅ Все сервисы успешно импортированы!")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def test_service_creation():
    """Тестирует создание экземпляров сервисов."""
    print("\n🧪 Тестируем создание экземпляров сервисов...")
    
    try:
        from core.tender_database import TenderDatabaseManager
        from config.settings import Config
        
        # Создаем мок-конфиг и менеджер БД
        config = Config()
        db_manager = TenderDatabaseManager(config)
        
        # Пытаемся создать сервисы
        from services.match_services.match_result_service import MatchResultService
        from services.match_services.match_query_service import MatchQueryService
        from services.match_services.match_status_service import MatchStatusService
        from services.match_services.tender_lock_service import TenderLockService
        from services.match_services.match_detail_service import MatchDetailService
        from services.match_services.file_error_service import FileErrorService
        from services.match_services.match_coordinator import MatchCoordinator
        from services.match_services.tender_match_repository_facade import TenderMatchRepositoryFacade
        
        services = [
            MatchResultService(db_manager),
            MatchQueryService(db_manager),
            MatchStatusService(db_manager),
            TenderLockService(db_manager),
            MatchDetailService(db_manager),
            FileErrorService(db_manager),
            MatchCoordinator(db_manager),
            TenderMatchRepositoryFacade(db_manager)
        ]
        
        print("✅ Все сервисы успешно созданы!")
        print(f"   Создано {len(services)} сервисов")
        
        # Проверяем, что у фасада есть все методы
        facade = TenderMatchRepositoryFacade(db_manager)
        required_methods = [
            'save_match_result', 'save_match_details', 'save_file_errors',
            'get_match_result', 'get_match_result_by_folder_name', 'get_match_summary',
            'get_match_details', 'get_match_results_batch', 'set_interesting_status',
            'filter_uninteresting_tenders', 'acquire_tender_lock', 'release_tender_lock',
            '_table_exists', '_fetch_match_id'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(facade, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Отсутствуют методы в фасаде: {missing_methods}")
            return False
        else:
            print("✅ Фасад имеет все необходимые методы!")
            return True
        
    except Exception as e:
        print(f"❌ Ошибка создания сервисов: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_facade_method_signatures():
    """Тестирует сигнатуры методов фасада."""
    print("\n🧪 Тестируем сигнатуры методов фасада...")
    
    try:
        from core.tender_database import TenderDatabaseManager
        from config.settings import Config
        from services.match_services.tender_match_repository_facade import TenderMatchRepositoryFacade
        
        config = Config()
        db_manager = TenderDatabaseManager(config)
        facade = TenderMatchRepositoryFacade(db_manager)
        
        # Проверяем несколько ключевых методов
        # Примечание: self не считается в сигнатуре при вызове
        methods_to_check = [
            ('save_match_result', 10),  # 10 параметров (без self)
            ('save_match_details', 2),  # 2 параметра (без self)
            ('save_file_errors', 2),     # 2 параметра (без self)
            ('get_match_result', 2),     # 2 параметра (без self)
        ]
        
        import inspect
        
        for method_name, expected_params in methods_to_check:
            method = getattr(facade, method_name)
            sig = inspect.signature(method)
            
            if len(sig.parameters) != expected_params:
                print(f"❌ Метод {method_name} имеет {len(sig.parameters)} параметров, ожидалось {expected_params}")
                return False
            else:
                print(f"✅ Метод {method_name} - OK ({len(sig.parameters)} параметров)")
        
        print("✅ Все сигнатуры методов корректны!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки сигнатур: {e}")
        return False

def main():
    """Основная функция тестирования."""
    print("🚀 Запуск тестов декомпозиции TenderMatchRepository")
    print("=" * 60)
    
    tests = [
        test_service_imports,
        test_service_creation,
        test_facade_method_signatures
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Тест {test.__name__} упал с ошибкой: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 Результаты тестирования:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Пройдено: {passed}/{total}")
    print(f"❌ Провалено: {total - passed}/{total}")
    
    if all(results):
        print("🎉 Все тесты пройдены успешно! Декомпозиция завершена.")
        return True
    else:
        print("⚠️  Некоторые тесты провалились. Требуется доработка.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)