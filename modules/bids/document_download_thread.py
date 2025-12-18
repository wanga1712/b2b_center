"""
Модуль для асинхронного скачивания документов в отдельном потоке.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt5.QtCore import QThread, pyqtSignal

from loguru import logger

from services.document_search.document_downloader import DocumentDownloader


class DocumentDownloadThread(QThread):
    """Поток для асинхронного скачивания документов"""
    
    progress_updated = pyqtSignal(int, int, str)  # current, total, file_name
    finished = pyqtSignal(int, int, Path)  # downloaded_count, total_count, download_dir
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, document_links: List[Dict[str, Any]], download_dir: Path, tender_data: Dict[str, Any]):
        super().__init__()
        self.document_links = document_links
        self.download_dir = download_dir
        self.tender_data = tender_data
    
    def run(self):
        """Выполнение скачивания документов"""
        try:
            registry_type = self._determine_registry_type()
            tender_id = self.tender_data.get('id')
            
            if tender_id:
                folder_name = f"{registry_type}_{tender_id}"
            else:
                folder_name = "tender_temp"
            
            tender_folder = self.download_dir / folder_name
            tender_folder.mkdir(parents=True, exist_ok=True)
            
            downloader = DocumentDownloader(tender_folder)
            
            total_docs = len(self.document_links)
            downloaded_count = 0
            batch_size = 8
            
            for start_idx in range(0, total_docs, batch_size):
                end_idx = min(start_idx + batch_size, total_docs)
                batch = self.document_links[start_idx:end_idx]
                
                logger.info(f"Скачивание документов {start_idx + 1}-{end_idx} из {total_docs} (параллельно)")
                
                with ThreadPoolExecutor(max_workers=min(batch_size, len(batch))) as executor:
                    future_to_doc = {
                        executor.submit(self._download_single_document, downloader, doc, tender_folder): doc
                        for doc in batch
                        if doc.get('document_links')
                    }
                    
                    for future in as_completed(future_to_doc):
                        doc = future_to_doc[future]
                        file_name = doc.get('file_name', 'Документ')
                        try:
                            downloaded_path = future.result()
                            if downloaded_path:
                                downloaded_count += 1
                                self.progress_updated.emit(downloaded_count, total_docs, file_name)
                                logger.info(f"✅ Скачан: {file_name}")
                        except Exception as error:
                            logger.error(f"❌ Ошибка при скачивании {file_name}: {error}")
                            continue
            
            self.finished.emit(downloaded_count, total_docs, tender_folder)
            
        except Exception as error:
            logger.error(f"Критическая ошибка при скачивании документов: {error}")
            self.error_occurred.emit(f"Ошибка при скачивании документов: {str(error)}")
    
    def _download_single_document(self, downloader: DocumentDownloader, doc: Dict[str, Any], target_dir: Path) -> Optional[Path]:
        """Скачивание одного документа"""
        try:
            return downloader.download_document(doc, target_dir=target_dir)
        except Exception as error:
            logger.error(f"Ошибка при скачивании документа: {error}")
            return None
    
    def _determine_registry_type(self) -> str:
        """Определяет тип реестра (44ФЗ/223ФЗ)"""
        raw_value = (
            self.tender_data.get('registry_type')
            or self.tender_data.get('law')
            or ''
        )
        value = str(raw_value).lower()
        if '223' in value:
            return '223fz'
        return '44fz'

