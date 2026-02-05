"""
MODULE: services.archive_background_runner
RESPONSIBILITY: Facade for backward compatibility with ArchiveBackgroundRunner interface.
ALLOWED: ArchiveProcessingService, logging, configuration.
FORBIDDEN: Business logic - delegate to ArchiveProcessingService.
ERRORS: Use ErrorHandler for all error handling.

Фасад для обратной совместимости с интерфейсом ArchiveBackgroundRunner.
Делегирует всю работу ArchiveProcessingService.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from loguru import logger

from core.database import DatabaseManager
from core.tender_database import TenderDatabaseManager
from services.archive_processing_service import ArchiveProcessingService


class ArchiveBackgroundRunner:
    """
    Фасад для обратной совместимости с интерфейсом ArchiveBackgroundRunner.
    Делегирует всю работу ArchiveProcessingService.
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
        """Инициализация фасада с теми же параметрами."""
        self.tender_db_manager = tender_db_manager
        self.product_db_manager = product_db_manager
        self.user_id = user_id
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.batch_delay = batch_delay

        # Создаем реальный сервис обработки
        self._processing_service = ArchiveProcessingService(
            tender_db_manager=tender_db_manager,
            product_db_manager=product_db_manager,
            user_id=user_id,
            max_workers=max_workers,
            batch_size=batch_size,
            batch_delay=batch_delay,
        )

        logger.info("✅ ArchiveBackgroundRunner фасад инициализирован")
        logger.info(f"   Параметры: user_id={user_id}, max_workers={max_workers}, "
                   f"batch_size={batch_size}, batch_delay={batch_delay}")

    def run(self, specific_tender_ids: Optional[List[Dict[str, Any]]] = None, 
            registry_type: Optional[str] = None, tender_type: str = 'new') -> Dict[str, Any]:
        """
        Запуск обработки через фасад.
        
        Args:
            specific_tender_ids: Список конкретных тендеров для обработки
            registry_type: Тип реестра ('44fz' или '223fz')
            tender_type: Тип торгов ('new' или 'won')
            
        Returns:
            Результаты обработки в том же формате
        """
        logger.info("🚀 Запуск обработки через фасад ArchiveBackgroundRunner")
        
        if specific_tender_ids:
            logger.info(f"   Обработка {len(specific_tender_ids)} конкретных тендеров")
        else:
            logger.info("   Обработка всех тендеров по настройкам пользователя")
        
        if registry_type:
            logger.info(f"   Тип реестра: {registry_type}")
        
        logger.info(f"   Тип торгов: {tender_type}")

        # Делегируем обработку реальному сервису
        try:
            result = self._processing_service.run(
                specific_tender_ids=specific_tender_ids,
                registry_type=registry_type,
                tender_type=tender_type
            )
            
            logger.info("✅ Обработка через фасад завершена успешно")
            return self._format_legacy_result(result)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки через фасад: {e}")
            return self._format_error_result(e)

    def _format_legacy_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Форматирование результата в legacy-формат."""
        # Преобразуем новый формат в старый для совместимости
        return {
            'processed': result.get('total_processed', 0),
            'successful': result.get('successful', 0),
            'failed': result.get('failed', 0),
            'total_tenders': result.get('total_processed', 0),
            'total_matches': 0,  # TODO: Добавить подсчет совпадений
            'errors': result.get('errors', []),
            'existing_folders_processed': result.get('existing_folders_processed', 0),
            'new_tenders_processed': result.get('new_tenders_processed', 0)
        }

    def _format_error_result(self, error: Exception) -> Dict[str, Any]:
        """Форматирование результата ошибки."""
        return {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'total_tenders': 0,
            'total_matches': 0,
            'errors': [str(error)],
            'existing_folders_processed': 0,
            'new_tenders_processed': 0
        }

    # Методы для полной совместимости (если потребуются)
    def process_existing_folders(self, registry_type: Optional[str] = None, 
                               tender_type: str = 'new') -> int:
        """Обработка существующих папок."""
        return self._processing_service.process_existing_folders(
            registry_type=registry_type,
            tender_type=tender_type
        )

    def process_new_tenders(self, registry_type: Optional[str] = None, 
                          tender_type: str = 'new') -> Dict[str, Any]:
        """Обработка новых тендеров."""
        result = self._processing_service.process_new_tenders(
            registry_type=registry_type,
            tender_type=tender_type
        )
        return self._format_legacy_result(result)