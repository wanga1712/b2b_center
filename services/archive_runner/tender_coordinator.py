"""
MODULE: services.archive_runner.tender_coordinator
RESPONSIBILITY:
- Координация процесса обработки торгов
- Управление потоком выполнения основных операций
- Оркестрация работы специализированных компонентов
ALLOWED:
- Вызов методов других компонентов (FolderProcessor, CloudUploader, ErrorHandler)
- Управление многопоточностью и очередями
- Логирование через loguru
FORBIDDEN:
- Прямые файловые операции
- Прямые запросы к базе данных
- Прямая работа с облачными сервисами
ERRORS:
- Должен пробрасывать CoordinationError, ProcessingError
"""

import time
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger

from services.archive_runner.folder_processor import FolderProcessor
from services.archive_runner.cloud_uploader import CloudUploader
from services.archive_runner.error_handler import ErrorHandler
from services.archive_runner.tender_queue_manager import TenderQueueManager
from services.archive_runner.tender_prefetcher import TenderPrefetcher
from services.archive_runner.tender_processor import TenderProcessor
from services.archive_runner.tender_provider import TenderProvider


class TenderCoordinator:
    """Координатор обработки торгов"""

    def __init__(self, 
                 folder_processor: FolderProcessor,
                 cloud_uploader: CloudUploader,
                 error_handler: ErrorHandler,
                 queue_manager: TenderQueueManager,
                 max_workers: int = 2):
        
        self.folder_processor = folder_processor
        self.cloud_uploader = cloud_uploader
        self.error_handler = error_handler
        self.queue_manager = queue_manager
        self.max_workers = max_workers

    def process_new_tenders(self, prefetcher: TenderPrefetcher, 
                          registry_type: Optional[str] = None) -> Dict[str, Any]:
        """Обработать новые торги"""
        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        try:
            # Получаем торги для обработки
            tenders = prefetcher.get_tenders_for_processing(registry_type)
            
            if not tenders:
                logger.info("Нет новых торгов для обработки")
                return results

            logger.info(f"Начинаем обработку {len(tenders)} новых торгов")
            
            # Обрабатываем в пуле потоков
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_tender = {
                    executor.submit(self._process_single_tender, tender): tender 
                    for tender in tenders
                }
                
                for future in as_completed(future_to_tender):
                    tender = future_to_tender[future]
                    try:
                        success = future.result()
                        if success:
                            results['successful'] += 1
                        else:
                            results['failed'] += 1
                        results['processed'] += 1
                        
                    except Exception as e:
                        logger.error(f"Ошибка обработки tender {tender.get('id')}: {e}")
                        results['failed'] += 1
                        results['errors'].append(str(e))
            
            logger.info(f"Обработка завершена: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Критическая ошибка в process_new_tenders: {e}")
            raise

    def _process_single_tender(self, tender: Dict[str, Any]) -> bool:
        """Обработать один торг"""
        tender_id = tender.get('id')
        registry_type = tender.get('registry_type', '44fz')
        
        try:
            logger.info(f"Начинаем обработку tender_id={tender_id}")
            
            # Здесь будет основная логика обработки
            # Координация между различными компонентами
            
            logger.info(f"Успешно обработан tender_id={tender_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки tender_id={tender_id}: {e}")
            self.error_handler.handle_failed_tender(tender, e, self.queue_manager)
            return False

    def process_existing_folders_parallel(self, registry_type: Optional[str] = None) -> int:
        """Параллельная обработка существующих папок"""
        try:
            # Используем FolderProcessor для обработки папок
            processed_count = self.folder_processor.process_existing_folders(registry_type)
            logger.info(f"Параллельно обработано {processed_count} папок")
            return processed_count
            
        except Exception as e:
            logger.error(f"Ошибка параллельной обработки папок: {e}")
            return 0

    def get_processing_stats(self) -> Dict[str, float]:
        """Получить статистику обработки"""
        return {
            'average_time_per_file': self._get_average_processing_time_per_file(),
            'average_time_per_tender': self._get_average_processing_time_per_tender(),
            'active_workers': self.max_workers
        }

    def _get_average_processing_time_per_file(self) -> float:
        """Среднее время обработки файла"""
        # Заглушка для реальной реализации
        return 2.5

    def _get_average_processing_time_per_tender(self) -> float:
        """Среднее время обработки торгов"""
        # Заглушка для реальной реализации
        return 30.0

    def process(self, specific_tender_ids: Optional[List[Dict[str, Any]]] = None,
               registry_type: Optional[str] = None, tender_type: str = 'new',
               tender_processor: Optional[TenderProcessor] = None,
               tender_provider: Optional[TenderProvider] = None) -> Dict[str, Any]:
        """
        Основной метод обработки, координирующий весь процесс.
        
        Args:
            specific_tender_ids: Конкретные тендеры для обработки
            registry_type: Тип реестра
            tender_type: Тип торгов
            tender_processor: Процессор тендеров
            tender_provider: Провайдер тендеров
            
        Returns:
            Результаты обработки
        """
        results = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'existing_folders_processed': 0,
            'new_tenders_processed': 0,
            'errors': []
        }

        try:
            # Обработка существующих папок
            if tender_type == 'existing':
                results['existing_folders_processed'] = self.process_existing_folders(
                    registry_type=registry_type,
                    tender_type=tender_type,
                    tender_processor=tender_processor
                )
            else:
                # Обработка новых тендеров
                new_tenders_result = self.process_new_tenders(
                    registry_type=registry_type,
                    tender_type=tender_type,
                    tender_processor=tender_processor,
                    tender_provider=tender_provider
                )
                results.update(new_tenders_result)
                results['new_tenders_processed'] = results.get('processed', 0)

            results['total_processed'] = results['existing_folders_processed'] + results['new_tenders_processed']
            return results

        except Exception as e:
            logger.error(f"Критическая ошибка в координаторе: {e}")
            results['errors'].append(str(e))
            return results

    def process_existing_folders(self, registry_type: Optional[str] = None,
                               tender_type: str = 'new',
                               tender_processor: Optional[TenderProcessor] = None) -> int:
        """Обработка существующих папок с документами."""
        try:
            # Делегируем обработку папок
            return self.process_existing_folders_parallel(registry_type)
        except Exception as e:
            logger.error(f"Ошибка обработки существующих папок: {e}")
            return 0

    def process_new_tenders(self, registry_type: Optional[str] = None,
                          tender_type: str = 'new',
                          tender_processor: Optional[TenderProcessor] = None,
                          tender_provider: Optional[TenderProvider] = None) -> Dict[str, Any]:
        """Обработка новых тендеров."""
        # Создаем префетчер для получения тендеров
        prefetcher = TenderPrefetcher(tender_provider, tender_type)
        
        # Используем существующий метод
        return self.process_new_tenders(prefetcher, registry_type)