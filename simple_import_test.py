"""Простой тест импортов для проверки структуры."""

import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_import():
    """Тестирует импорт каждого сервиса по отдельности."""
    
    services_to_test = [
        "services.tender_services.okpd_service.OKPDService",
        "services.tender_services.user_settings_service.UserSettingsService", 
        "services.tender_services.tender_feed_service.TenderFeedService",
        "services.tender_services.document_service.DocumentService",
        "services.tender_services.tender_coordinator.TenderCoordinator",
        "services.tender_services.tender_repository_facade.TenderRepositoryFacade"
    ]
    
    for service_path in services_to_test:
        try:
            module_name, class_name = service_path.rsplit('.', 1)
            module = __import__(module_name, fromlist=[class_name])
            service_class = getattr(module, class_name)
            print(f"✅ {service_path}")
        except ImportError as e:
            print(f"❌ {service_path}: {e}")
            return False
        except AttributeError as e:
            print(f"❌ {service_path}: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🧪 Тестируем импорт сервисов...")
    success = test_import()
    if success:
        print("🎉 Все импорты успешны!")
    else:
        print("⚠️  Есть проблемы с импортами")
    sys.exit(0 if success else 1)