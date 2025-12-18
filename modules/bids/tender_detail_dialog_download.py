"""Модуль для обработки скачивания документов в диалоге."""

from pathlib import Path
from PyQt5.QtWidgets import QMessageBox
from loguru import logger
from modules.bids.document_download_thread import DocumentDownloadThread
from config.settings import config


def handle_download_all_documents(dialog, document_links: list, tender_data: dict):
    """Обработчик скачивания всех документов"""
    if not document_links:
        QMessageBox.warning(dialog, "Предупреждение", "Нет документов для скачивания")
        return
    
    download_dir = Path(config.document_download_dir) if config.document_download_dir else None
    if not download_dir:
        QMessageBox.warning(
            dialog,
            "Ошибка",
            "Не настроен путь для скачивания документов.\n"
            "Установите переменную DOCUMENT_DOWNLOAD_DIR в .env файле."
        )
        return
    
    download_thread = DocumentDownloadThread(document_links, download_dir, tender_data)
    download_thread.progress_updated.connect(
        lambda current, total, file_name: logger.info(f"Скачивание: {current}/{total} - {file_name}")
    )
    download_thread.finished.connect(
        lambda downloaded_count, total_count, download_dir: QMessageBox.information(
            dialog,
            "Скачивание завершено",
            f"Скачано документов: {downloaded_count} из {total_count}\n"
            f"Файлы сохранены в: {download_dir}"
        )
    )
    download_thread.error_occurred.connect(
        lambda error_message: QMessageBox.critical(dialog, "Ошибка", error_message)
    )
    download_thread.start()
    
    QMessageBox.information(
        dialog,
        "Скачивание документов",
        f"Начато скачивание {len(document_links)} документов.\n"
        f"Файлы будут сохранены в: {download_dir}"
    )

