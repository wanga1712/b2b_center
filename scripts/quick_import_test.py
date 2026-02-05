#!/usr/bin/env python3
"""
MODULE: scripts.quick_import_test
RESPONSIBILITY: Testing imports to verify environment setup.
ALLOWED: sys, pathlib, config.settings, services.archive_runner.workbook_manager, services.archive_runner.runner, traceback.
FORBIDDEN: None.
ERRORS: None.

Быстрый тест импортов
"""

import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("Тестирование импортов...")

try:
    from config.settings import config
    print("✅ config imported")
except Exception as e:
    print(f"❌ config import error: {e}")
    sys.exit(1)

try:
    from services.archive_runner.workbook_manager import WorkbookManager
    print("✅ WorkbookManager imported")
except Exception as e:
    print(f"❌ WorkbookManager import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from services.archive_runner.runner import ArchiveBackgroundRunner
    print("✅ ArchiveBackgroundRunner imported")
except Exception as e:
    print(f"❌ ArchiveBackgroundRunner import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("🎉 Все импорты успешны!")
