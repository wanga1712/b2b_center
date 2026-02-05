"""
Тест декомпозиции TenderRepository.

Проверяет, что все сервисы успешно импортируются и создаются,
а фасад предоставляет тот же интерфейс, что и оригинальный TenderRepository.
"""

import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Тестирует импорт всех сервисов."""
    print("🧪 Тестируем импорт сервисов...")
    
    try:
        # Импортируем каждый сервис отдельно
        from services.tender_services.okpd_service import OKPDService
        from services.tender_services.user_settings_service import UserSettingsService
        from services.tender_services.tender_feed_service import TenderFeedService
        from services.tender_services.document_service import DocumentService
        from services.tender_services.tender_coordinator import TenderCoordinator
        from services.tender_services.tender_repository_facade import TenderRepositoryFacade
        
        # Проверяем, что классы действительно импортированы
        assert OKPDService is not None
        assert UserSettingsService is not None
        assert TenderFeedService is not None
        assert DocumentService is not None
        assert TenderCoordinator is not None
        assert TenderRepositoryFacade is not None
        
        print("✅ Все сервисы успешно импортированы!")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def test_service_creation():
    """Тестирует создание экземпляров сервисов."""
    print("🧪 Тестируем создание экземпляров сервисов...")
    
    try:
        # Имитируем db_manager для тестов
        class MockDBManager:
            pass
        
        db_manager = MockDBManager()
        
        # Создаем все сервисы
        okpd_service = OKPDService(db_manager)
        user_settings_service = UserSettingsService(db_manager)
        tender_feed_service = TenderFeedService(db_manager)
        document_service = DocumentService(db_manager)
        coordinator = TenderCoordinator(db_manager)
        facade = TenderRepositoryFacade(db_manager)
        
        print(f"✅ Все сервисы успешно созданы!")
        print(f"   Создано 6 сервисов")
        
        # Проверяем, что фасад имеет все необходимые методы
        required_methods = [
            'search_okpd_codes', 'get_all_okpd_codes', 'get_user_okpd_codes',
            'add_user_okpd_code', 'remove_user_okpd_code', 'get_okpd_by_code',
            'save_user_search_settings', 'get_user_search_settings', 'get_all_regions',
            'search_okpd_codes_by_region', 'get_user_stop_words', 'add_user_stop_words',
            'remove_user_stop_word', 'get_document_stop_phrases', 'add_document_stop_phrases',
            'remove_document_stop_phrase', 'get_user_search_phrases', 'add_user_search_phrases',
            'remove_user_search_phrase', 'get_new_tenders_44fz', 'get_new_tenders_223fz',
            'get_won_tenders_44fz', 'get_won_tenders_223fz', 'get_commission_tenders_44fz',
            'get_tender_documents', 'get_tenders_by_ids', 'get_okpd_categories',
            'create_okpd_category', 'update_okpd_category', 'delete_okpd_category',
            'assign_okpd_to_category', 'get_okpd_codes_by_category'
        ]
        
        for method in required_methods:
            if not hasattr(facade, method):
                print(f"❌ Метод {method} отсутствует в фасаде")
                return False
        
        print("✅ Фасад имеет все необходимые методы!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания сервисов: {e}")
        return False

def test_method_signatures():
    """Тестирует сигнатуры методов фасада."""
    print("🧪 Тестируем сигнатуры методов фасада...")
    
    try:
        from inspect import signature
        
        class MockDBManager:
            pass
        
        db_manager = MockDBManager()
        facade = TenderRepositoryFacade(db_manager)
        
        # Проверяем несколько ключевых методов
        methods_to_check = [
            ('search_okpd_codes', 2),      # 2 параметра (без self)
            ('get_user_okpd_codes', 2),    # 2 параметра (без self)
            ('save_user_search_settings', 3), # 3 параметра (без self)
            ('get_new_tenders_44fz', 3),   # 3 параметра (без self)
            ('get_tender_documents', 2),  # 2 параметра (без self)
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
        return False

def main():
    """Основная функция тестирования."""
    print("🚀 Запуск тестов декомпозиции TenderRepository")
    print("=" * 60)
    
    tests = [
        test_imports,
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