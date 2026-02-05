"""
Тест декомпозиции DocumentSearchService.

Проверяет, что все сервисы создаются корректно и предоставляют
полный интерфейс оригинального DocumentSearchService.
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
        from services.document_search.progress_service import ProgressService
        from services.document_search.tender_folder_service import TenderFolderService
        from services.document_search.workbook_processor import WorkbookProcessor
        from services.document_search.match_aggregator_service import MatchAggregatorService
        from services.document_search.document_search_coordinator import DocumentSearchCoordinator
        from services.document_search.document_search_facade import DocumentSearchFacade
        
        # Имитируем зависимости для тестов
        class MockDBManager:
            def execute_query(self, query, params=None):
                return []
        
        class MockArchiveExtractor:
            def extract_archive(self, path):
                return []
            def is_file_archive(self, path):
                return False
            def combine_multi_part_archive(self, paths):
                return paths[0] if paths else None
        
        db_manager = MockDBManager()
        download_dir = Path("test_temp")
        
        # Создаем все сервисы
        services = [
            ProgressService(None),
            TenderFolderService(download_dir),
            WorkbookProcessor(MockArchiveExtractor()),
            MatchAggregatorService(),
            DocumentSearchCoordinator(db_manager, download_dir),
            DocumentSearchFacade(db_manager, download_dir)
        ]
        
        print(f"✅ Все сервисы успешно созданы!")
        print(f"   Создано {len(services)} сервисов")
        
        # Проверяем, что фасад имеет все необходимые методы
        facade = DocumentSearchFacade(db_manager, download_dir)
        required_methods = [
            'run_document_search', 'ensure_products_loaded', '_update_progress',
            '_prepare_tender_folder', '_prepare_workbook_paths', '_aggregate_matches_for_workbooks'
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
        from services.document_search.document_search_facade import DocumentSearchFacade
        from inspect import signature
        
        class MockDBManager:
            def execute_query(self, query, params=None):
                return []
        
        db_manager = MockDBManager()
        download_dir = Path("test_temp")
        facade = DocumentSearchFacade(db_manager, download_dir)
        
        # Проверяем основной метод
        method = getattr(facade, 'run_document_search')
        sig = signature(method)
        actual_params = len(sig.parameters)
        
        # run_document_search должен иметь 3 параметра (documents, tender_id, registry_type) без self
        if actual_params == 3:
            print(f"✅ Метод run_document_search - OK ({actual_params} параметров)")
        else:
            print(f"❌ Метод run_document_search имеет {actual_params} параметров, ожидалось 3")
            return False
        
        print("✅ Сигнатуры методов корректны!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки сигнатур: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция тестирования."""
    print("🚀 Запуск тестов декомпозиции DocumentSearchService")
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