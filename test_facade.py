#!/usr/bin/env python3
"""
Тестовый скрипт для проверки фасада ArchiveBackgroundRunnerFacade
"""

import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent))

def test_facade_import():
    """Тест импорта фасада"""
    print("🧪 Тестируем импорт фасада...")
    
    try:
        from services.archive_runner.runner_facade import ArchiveBackgroundRunnerFacade
        print("✅ Фасад успешно импортирован!")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта фасада: {e}")
        return False

def test_facade_creation():
    """Тест создания экземпляра фасада"""
    print("\n🧪 Тестируем создание экземпляра фасада...")
    
    try:
        from services.archive_runner.runner_facade import ArchiveBackgroundRunnerFacade
        from core.tender_database import TenderDatabaseManager
        from config.settings import Config
        
        # Создаем мок-объекты для теста
        config = Config()
        tender_db_manager = TenderDatabaseManager(config)
        product_db_manager = TenderDatabaseManager(config)
        
        # Пытаемся создать фасад
        facade = ArchiveBackgroundRunnerFacade(
            tender_db_manager=tender_db_manager,
            product_db_manager=product_db_manager,
            user_id=1
        )
        
        print("✅ Экземпляр фасада успешно создан!")
        print(f"   Тип объекта: {type(facade)}")
        print(f"   Имеет метод run: {hasattr(facade, 'run')}")
        print(f"   Имеет tender_repo: {hasattr(facade, 'tender_repo')}")
        print(f"   Имеет tender_match_repo: {hasattr(facade, 'tender_match_repo')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания фасада: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_alias():
    """Тест алиаса для обратной совместимости"""
    print("\n🧪 Тестируем алиас для обратной совместимости...")
    
    try:
        from services.archive_runner.runner_facade import ArchiveBackgroundRunner
        
        print("✅ Алиас ArchiveBackgroundRunner доступен!")
        print(f"   Тип алиаса: {ArchiveBackgroundRunner}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка доступа к алиасу: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Начинаем тестирование фасада ArchiveBackgroundRunnerFacade")
    print("=" * 60)
    
    success = True
    
    # Запускаем тесты
    success &= test_facade_import()
    success &= test_facade_creation() 
    success &= test_alias()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Все тесты пройдены успешно! Фасад готов к использованию.")
        return 0
    else:
        print("❌ Некоторые тесты не пройдены. Требуется доработка.")
        return 1

if __name__ == "__main__":
    sys.exit(main())