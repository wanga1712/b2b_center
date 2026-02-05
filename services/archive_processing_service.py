"""
MODULE: services.archive_processing_service
RESPONSIBILITY: Main service for coordinating archive processing with SRP compliance.
ALLOWED: All archive_runner components, logging, configuration.
FORBIDDEN: Direct file operations, business logic - delegate to specialized components.
ERRORS: Use ErrorHandler for all error handling.

Главный сервисный координатор обработки архивов с соблюдением SRP.
Делегирует всю работу специализированным компонентам.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger

from config.settings import config
from core.database import DatabaseManager
from core.tender_database import TenderDatabaseManager
from core.exceptions import DocumentSearchError, DatabaseConnectionError

# Импорт всех компонентов archive_runner
from services.archive_runner.tender_coordinator import TenderCoordinator
from services.archive_runner.folder_processor import FolderProcessor
from services.archive_runner.cloud_uploader import CloudUploader
from services.archive_runner.error_handler import ErrorHandler
from services.archive_runner.tender_queue_manager import TenderQueueManager
from services.archive_runner.tender_processor import TenderProcessor
from services.archive_runner.tender_folder_manager import TenderFolderManager
from services.archive_runner.processed_tenders_repository import ProcessedTendersRepository
from services.archive_runner.tender_provider import TenderProvider
from services.archive_runner.tender_prefetcher import TenderPrefetcher

# Импорт document_search компонентов
from services.document_search_service import DocumentSearchService
from services.document_search.document_selector import DocumentSelector
from services.document_search.document_downloader import DocumentDownloader
from services.document_search.download_timeout_calculator import create_timeout_calculator
from services.document_search.archive_extractor import ArchiveExtractor
from services.document_search.match_finder import MatchFinder

# Импорт репозиториев
from services.tender_services.tender_repository_facade import TenderRepositoryFacade
from services.match_services.tender_match_repository_facade import TenderMatchRepositoryFacade


class ArchiveProcessingService:
    """
    Главный сервис обработки архивов с соблюдением SRP.
    Координирует работу всех специализированных компонентов.
    """

    def __init__(
        self,
        tender_db_manager: TenderDatabaseManager,
        product_db_manager: DatabaseManager,
        user_id: int = 1,
        max_workers: int = 2,
        batch_size: int = 5,
        batch_delay: float = 10.0,
    ):
        """Инициализация сервиса с внедрением зависимостей."""
        self.tender_db_manager = tender_db_manager
        self.product_db_manager = product_db_manager
        self.user_id = user_id
        self.max_workers = max(1, max_workers)
        self.batch_size = max(1, batch_size)
        self.batch_delay = max(0.0, batch_delay)

        # Инициализация всех компонентов
        self._initialize_components()
        self._initialize_coordinator()

    def _initialize_components(self) -> None:
        """Инициализация всех специализированных компонентов."""
        # Репозитории
        self.tender_repo = TenderRepositoryFacade(self.tender_db_manager)
        self.tender_match_repo = TenderMatchRepository(self.tender_db_manager)
        self.processed_tenders_repo = ProcessedTendersRepository(self.tender_db_manager)
        self.tender_provider = TenderProvider(self.tender_repo, self.user_id)

        # Настройка путей
        download_dir = Path(config.document_download_dir) if config.document_download_dir else Path.home() / "Downloads" / "ЕИС_Документация"
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Сервисы поиска документов
        self.document_search_service = DocumentSearchService(
            self.product_db_manager,
            self.download_dir,
            unrar_path=config.unrar_tool,
            winrar_path=config.winrar_path,
        )
        self.document_search_service.ensure_products_loaded()

        self.selector = DocumentSelector()
        timeout_calculator = create_timeout_calculator(self.tender_db_manager)
        self.downloader = DocumentDownloader(
            self.download_dir,
            progress_callback=None,
            timeout_calculator=timeout_calculator
        )
        self.extractor = ArchiveExtractor(
            unrar_path=config.unrar_tool,
            winrar_path=config.winrar_path,
        )

        # Инициализация MatchFinder
        document_stop_phrases = self._get_document_stop_phrases()
        self.match_finder = MatchFinder(
            self.document_search_service._product_names,
            stop_phrases=document_stop_phrases,
            user_search_phrases=[],
        )

        # Менеджеры и процессоры
        self.folder_manager = TenderFolderManager(self.download_dir)
        self.folder_processor = FolderProcessor(self.folder_manager)
        self.cloud_uploader = CloudUploader(None)  # Яндекс Диск временно отключен
        self.error_handler = ErrorHandler(max_retries=3, retry_delay=2.0)

    def _initialize_coordinator(self) -> None:
        """Инициализация координатора обработки тендеров."""
        self.tender_processor = TenderProcessor(
            tender_match_repo=self.tender_match_repo,
            folder_manager=self.folder_manager,
            document_search_service=self.document_search_service,
            selector=self.selector,
            downloader=self.downloader,
            extractor=self.extractor,
            match_finder=self.match_finder,
            file_cleaner=None,  # Будет инициализирован в TenderProcessor
            processed_tenders_repo=self.processed_tenders_repo,
            max_workers=self.max_workers,
            safe_call_func=self.error_handler.safe_call,
            get_avg_time_func=self._get_average_processing_time_per_file,
            batch_delay=min(self.batch_delay, 5.0),
        )

        self.tender_coordinator = TenderCoordinator(
            folder_processor=self.folder_processor,
            cloud_uploader=self.cloud_uploader,
            error_handler=self.error_handler,
            queue_manager=TenderQueueManager(),
            max_workers=self.max_workers
        )

    def _get_document_stop_phrases(self) -> List[str]:
        """Получение стоп-фраз для анализа документации."""
        try:
            document_stop_phrases_rows = getattr(self.tender_repo, "get_document_stop_phrases", lambda _uid: [])(self.user_id)
            return [
                row.get("phrase", "").strip()
                for row in document_stop_phrases_rows
                if row.get("phrase")
            ]
        except Exception:
            return []

    def _get_average_processing_time_per_file(self) -> float:
        """Получение среднего времени обработки файла."""
        # Делегируем обработчику тендеров
        return self.tender_processor.get_average_processing_time_per_file()

    def run(self, specific_tender_ids: Optional[List[Dict[str, Any]]] = None, 
            registry_type: Optional[str] = None, tender_type: str = 'new') -> Dict[str, Any]:
        """
        Запуск обработки через координатор.
        
        Args:
            specific_tender_ids: Список конкретных тендеров для обработки
            registry_type: Тип реестра ('44fz' или '223fz')
            tender_type: Тип торгов ('new' или 'won')
            
        Returns:
            Результаты обработки
        """
        # Делегируем всю логику координатору
        return self.tender_coordinator.process(
            specific_tender_ids=specific_tender_ids,
            registry_type=registry_type,
            tender_type=tender_type,
            tender_processor=self.tender_processor,
            tender_provider=self.tender_provider
        )

    def process_existing_folders(self, registry_type: Optional[str] = None, 
                               tender_type: str = 'new') -> int:
        """Обработка существующих папок с документами."""
        return self.tender_coordinator.process_existing_folders(
            registry_type=registry_type,
            tender_type=tender_type,
            tender_processor=self.tender_processor
        )

    def process_new_tenders(self, registry_type: Optional[str] = None, 
                          tender_type: str = 'new') -> Dict[str, Any]:
        """Обработка новых тендеров."""
        return self.tender_coordinator.process_new_tenders(
            registry_type=registry_type,
            tender_type=tender_type,
            tender_processor=self.tender_processor,
            tender_provider=self.tender_provider
        )