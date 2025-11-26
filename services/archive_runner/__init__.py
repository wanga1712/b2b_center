"""
Модуль для автоматической обработки документов торгов.

Разделен на подмодули:
- file_cleaner: Очистка файлов после обработки
- existing_files_processor: Обработка существующих файлов
- tender_provider: Получение торгов из БД
- download_manager: Скачивание документов
"""

from services.archive_runner.runner import ArchiveBackgroundRunner

__all__ = ['ArchiveBackgroundRunner']

