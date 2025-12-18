"""
Основной модуль запуска автоматической обработки документов торгов.
"""

from __future__ import annotations

import os
import time
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger

from config.settings import config
from core.database import DatabaseManager
from core.tender_database import TenderDatabaseManager
from core.exceptions import DocumentSearchError, DatabaseConnectionError
from services.document_search_service import DocumentSearchService
from services.document_search.document_selector import DocumentSelector
from services.document_search.document_downloader import DocumentDownloader
from services.document_search.archive_extractor import ArchiveExtractor
from services.document_search.match_finder import MatchFinder
from services.tender_repository import TenderRepository
from services.tender_match_repository import TenderMatchRepository
from services.archive_runner.file_cleaner import FileCleaner
from services.archive_runner.existing_files_processor import ExistingFilesProcessor
from services.archive_runner.tender_provider import TenderProvider
from services.archive_runner.tender_folder_manager import TenderFolderManager
from services.archive_runner.tender_processor import TenderProcessor
from services.archive_runner.tender_prefetcher import TenderPrefetcher, PrefetchedTenderData


class ArchiveBackgroundRunner:
    """
    Координатор фоновой обработки документов:
    1. Обрабатывает уже скачанные файлы
    2. Скачивает новые документы
    3. Находит совпадения и сохраняет результаты
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
        self.tender_db_manager = tender_db_manager
        self.product_db_manager = product_db_manager
        self.user_id = user_id
        self.max_workers = max(1, max_workers)  # Минимум 1 поток
        self.batch_size = max(1, batch_size)  # Минимум 1 торг в батче
        self.batch_delay = max(0.0, batch_delay)  # Минимум 0 секунд задержки

        self.tender_repo = TenderRepository(tender_db_manager)
        self.tender_match_repo = TenderMatchRepository(tender_db_manager)
        self.tender_provider = TenderProvider(self.tender_repo, user_id)

        download_dir = Path(config.document_download_dir) if config.document_download_dir else Path.home() / "Downloads" / "ЕИС_Документация"
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.document_search_service = DocumentSearchService(
            product_db_manager,
            download_dir,
            unrar_path=config.unrar_tool,
            winrar_path=config.winrar_path,
        )
        self.document_search_service.ensure_products_loaded()

        self.selector = DocumentSelector()
        self.downloader = DocumentDownloader(download_dir, progress_callback=None)
        self.extractor = ArchiveExtractor(
            unrar_path=config.unrar_tool,
            winrar_path=config.winrar_path,
        )
        # Стоп-фразы для анализа документации (можно хранить на стороне tender_monitor)
        try:
            document_stop_phrases_rows = getattr(self.tender_repo, "get_document_stop_phrases", lambda _uid: [])(user_id)
            document_stop_phrases = [
                row.get("phrase", "").strip()
                for row in document_stop_phrases_rows
                if row.get("phrase")
            ]
        except Exception:
            document_stop_phrases = []

        self.match_finder = MatchFinder(self.document_search_service._product_names, stop_phrases=document_stop_phrases)
        self.file_cleaner = FileCleaner()
        self.existing_processor = ExistingFilesProcessor(download_dir)
        
        # Инициализируем менеджер папок и процессор тендеров
        self.folder_manager = TenderFolderManager(download_dir)
        self.tender_processor = TenderProcessor(
            tender_match_repo=self.tender_match_repo,
            folder_manager=self.folder_manager,
            document_search_service=self.document_search_service,
            selector=self.selector,
            downloader=self.downloader,
            extractor=self.extractor,
            match_finder=self.match_finder,
            file_cleaner=self.file_cleaner,
            max_workers=self.max_workers,
            safe_call_func=self._safe_tender_call,
            get_avg_time_func=self._get_average_processing_time_per_file,
            batch_delay=min(self.batch_delay, 5.0),  # Используем меньшую задержку для файлов
        )

        self._processed_tenders: Set[Tuple[int, str]] = set()
        self._reconnect_delay = 60

    def run(self, specific_tender_ids: Optional[List[Dict[str, Any]]] = None, registry_type: Optional[str] = None, tender_type: str = 'new') -> Dict[str, Any]:
        """
        Запуск полного цикла обработки:
        - сначала существующие файлы
        - затем новые торги из БД или конкретные закупки
        
        Args:
            specific_tender_ids: Список словарей с ключами 'id' и 'registry_type' для конкретных закупок
            registry_type: Тип реестра для фильтрации ('44fz' или '223fz'). Если None, обрабатываются оба.
            tender_type: Тип торгов ('new' для новых, 'won' для разыгранных). По умолчанию 'new'.
        """
        logger.info("🚀 Запуск автоматической обработки документов торгов")
        logger.info("=" * 80)

        overall_start = time.time()
        existing_processed = self._process_existing_folders(registry_type=registry_type, tender_type=tender_type)

        # Счетчики статистики
        processed = 0
        errors = 0
        skipped_no_docs = 0
        total_matches = 0

        # Если указаны конкретные закупки, используем их, иначе получаем по настройкам
        if specific_tender_ids:
            tenders = self._safe_tender_call(
                self.tender_provider.get_target_tenders,
                specific_tender_ids=specific_tender_ids,
                registry_type=registry_type,
                tender_type=tender_type
            )
        else:
            tenders = self._safe_tender_call(
                self.tender_provider.get_target_tenders,
                registry_type=registry_type,
                tender_type=tender_type
            )
        
        if not tenders:
            logger.warning("Нет торгов для обработки")

        processed = 0
        errors = 0
        skipped_no_docs = 0
        total_matches = 0
        total_tenders_count = len(tenders) if tenders else 0

        # Батч-проверка обработанных торгов одним запросом к БД
        processed_tenders_cache: Dict[Tuple[int, str], Dict[str, Any]] = {}
        if tenders:
            # Группируем торги по registry_type для батч-проверки
            tenders_by_registry: Dict[str, List[int]] = {}
            for tender in tenders:
                registry = tender.get("registry_type", "44fz")
                tender_id = tender.get("id")
                if tender_id:
                    if registry not in tenders_by_registry:
                        tenders_by_registry[registry] = []
                    tenders_by_registry[registry].append(tender_id)
            
            # Проверяем все торги батчами
            for registry, tender_ids in tenders_by_registry.items():
                batch_results = self._safe_tender_call(
                    self.tender_match_repo.get_match_results_batch,
                    tender_ids,
                    registry,
                )
                for tender_id, match_result in batch_results.items():
                    processed_tenders_cache[(tender_id, registry)] = match_result
            
            logger.info(
                f"Батч-проверка: из {total_tenders_count} торгов уже обработано: {len(processed_tenders_cache)}"
            )

        # Получаем среднее время обработки одного торга из БД для расчета оставшегося времени
        avg_time_per_tender = self._get_average_processing_time_per_tender()

        prefetcher: Optional[TenderPrefetcher] = None
        if tenders:
            prefetcher = self._create_prefetcher(tender_type)
            prefetcher.schedule(tenders, self._get_tender_documents_safe)

        # Приоритизация по размеру папок: скачиваем документы для всех тендеров,
        # затем определяем размеры папок и сортируем от меньшего к большему
        tenders_with_sizes, original_index_map = self._prepare_tenders_with_sizes(tenders, prefetcher, tender_type)
        
        # Обрабатываем торги партиями для снижения нагрузки на CPU
        batch_number = 0
        for index, (tender, folder_size) in enumerate(tenders_with_sizes):
            try:
                tender_id = tender.get("id")
                registry_type = tender.get("registry_type", "44fz")
                key = (tender_id, registry_type)
                
                # Проверяем кэш обработанных торгов (быстрее чем запрос к БД)
                if key in processed_tenders_cache:
                    match_result = processed_tenders_cache[key]
                    self.tender_processor._log_already_processed(tender_id, registry_type, match_result)
                    self._processed_tenders.add(key)
                    continue
                
                if key in self._processed_tenders:
                    logger.info(f"Торг {tender_id} ({registry_type}) уже был обработан, пропускаем")
                    continue

                # Рассчитываем оставшееся время на основе среднего времени обработки
                remaining_tenders = total_tenders_count - processed - errors - skipped_no_docs
                if avg_time_per_tender > 0 and remaining_tenders > 0:
                    estimated_remaining_seconds = remaining_tenders * avg_time_per_tender
                    time_str = self._format_eta(estimated_remaining_seconds)
                    size_mb = folder_size / (1024 * 1024)
                    logger.info(f"Обработка торга {index + 1}/{total_tenders_count} (размер папки: {size_mb:.2f} МБ). Осталось примерно: {time_str}")

                # Получаем prefetched_data с учетом оригинального индекса до сортировки
                original_index = original_index_map.get(id(tender), index)
                prefetched_data = prefetcher.get_prefetched_data(original_index, tender) if prefetcher else None
                tender_start_time = time.time()
                result = self._process_tender(tender, prefetched_data=prefetched_data, processed_tenders_cache=processed_tenders_cache, tender_type=tender_type)
                tender_elapsed = time.time() - tender_start_time
                
                if result:
                    # Проверяем причину пропуска
                    reason = result.get("reason")
                    if reason == "no_documents":
                        # Отсутствие документов - это нормально, не ошибка
                        skipped_no_docs += 1
                        self._processed_tenders.add(key)
                        logger.debug(f"⏭️ Торг {tender_id} ({registry_type}) пропущен: нет документов")
                    elif reason == "already_processed":
                        # Уже обработан - тоже нормально
                        processed += 1
                        match_count = result.get("match_count", 0)
                        total_matches += match_count
                        self._processed_tenders.add(key)
                        logger.debug(f"⏭️ Торг {tender_id} ({registry_type}) уже обработан ранее")
                    else:
                        # Нормальная обработка
                        processed += 1
                        match_count = result.get("match_count", 0)
                        total_matches += match_count
                        self._processed_tenders.add(key)
                        
                        # Показываем результат обработки
                        if match_count > 0:
                            logger.info(f"✅ Торг {tender_id} ({registry_type}) обработан за {tender_elapsed:.1f} сек. Найдено совпадений: {match_count}")
                        else:
                            logger.info(f"⚠️ Торг {tender_id} ({registry_type}) обработан за {tender_elapsed:.1f} сек. Совпадений не найдено")
                else:
                    errors += 1
                    # Детальное логирование ошибки
                    error_details = result if isinstance(result, dict) else {}
                    error_reason = error_details.get("reason", "unknown")
                    error_message = error_details.get("error_message", "Неизвестная ошибка")
                    error_saved = error_details.get("error_saved", False)
                    
                    logger.warning(
                        f"❌ Ошибка обработки торга {tender_id} ({registry_type}): "
                        f"reason={error_reason}, message={error_message}, saved_to_db={error_saved}"
                    )
                    if error_reason == "unknown" and not error_message:
                        logger.debug(f"Полный результат обработки: {result}")
                
                # Добавляем паузу после каждого батча торгов для охлаждения процессора
                if (index + 1) % self.batch_size == 0 and index < len(tenders) - 1:
                    batch_number += 1
                    remaining_batches = (len(tenders) - index - 1) // self.batch_size + (1 if (len(tenders) - index - 1) % self.batch_size > 0 else 0)
                    logger.info(f"⏸️  Пауза после батча {batch_number}. Осталось батчей: {remaining_batches}. Охлаждение процессора {self.batch_delay:.1f} сек...")
                    time.sleep(self.batch_delay)
            except Exception as e:
                # Критическая ошибка при обработке одного тендера - логируем и продолжаем
                errors += 1
                tender_id = tender.get("id", "unknown")
                registry_type = tender.get("registry_type", "unknown")
                logger.error(f"❌ Критическая ошибка при обработке торга {tender_id} ({registry_type}): {e}", exc_info=True)
                # Продолжаем обработку следующих тендеров

        if prefetcher:
            prefetcher.shutdown()

        overall_time = time.time() - overall_start

        logger.info(f"\n{'='*80}")
        logger.info("📊 ИТОГОВАЯ СТАТИСТИКА")
        logger.info(f"{'='*80}")
        logger.info(f"📁 Обработано существующих директорий: {existing_processed}")
        logger.info(f"📦 Новых торгов: {len(tenders)}")
        logger.info(f"✅ Успешно обработано: {processed}")
        logger.info(f"⏭️ Пропущено (нет документов): {skipped_no_docs}")
        logger.info(f"❌ Ошибок: {errors}")
        logger.info(f"🔍 Всего найдено совпадений: {total_matches}")
        logger.info(f"⏱️  Общее время: {overall_time:.2f} сек")

        return {
            "existing_processed": existing_processed,
            "total_tenders": len(tenders),
            "processed": processed,
            "errors": errors,
            "total_matches": total_matches,
            "total_time": overall_time,
        }

    def _process_existing_folders(self, registry_type: Optional[str] = None, tender_type: str = 'new') -> int:
        """
        Обрабатывает уже скачанные файлы в директориях.
        
        Args:
            registry_type: Тип реестра для фильтрации ('44fz' или '223fz')
            tender_type: Тип торгов ('new' для новых, 'won' для разыгранных)
        """
        entries = self.existing_processor.list_pending_tenders()
        logger.info(f"Найдено директорий с существующими файлами: {len(entries)}")
        
        if not entries:
            return 0
        
        # Батч-проверка обработанных торгов для существующих файлов
        tenders_by_registry: Dict[str, List[int]] = {}
        for entry in entries:
            # Фильтруем по registry_type
            if registry_type and entry.get("registry_type") != registry_type:
                continue
            # Фильтруем по tender_type - обрабатываем только соответствующий тип
            entry_tender_type = entry.get("tender_type", "new")
            if entry_tender_type != tender_type:
                continue
            reg = entry.get("registry_type", "44fz")
            tender_id = entry.get("tender_id")
            if tender_id:
                if reg not in tenders_by_registry:
                    tenders_by_registry[reg] = []
                tenders_by_registry[reg].append(tender_id)
        
        processed_tenders_cache: Dict[Tuple[int, str], Dict[str, Any]] = {}
        for reg, tender_ids in tenders_by_registry.items():
            batch_results = self._safe_tender_call(
                self.tender_match_repo.get_match_results_batch,
                tender_ids,
                reg,
            )
            for tender_id, match_result in batch_results.items():
                processed_tenders_cache[(tender_id, reg)] = match_result
        
        filtered_count = len([e for e in entries if (not registry_type or e.get("registry_type") == registry_type) and e.get("tender_type", "new") == tender_type])
        logger.info(
            f"Батч-проверка существующих файлов ({tender_type}): из {filtered_count} торгов уже обработано: {len(processed_tenders_cache)}"
        )
        
        processed = 0
        for entry in entries:
            # Фильтруем по registry_type
            if registry_type and entry.get("registry_type") != registry_type:
                continue
            # Фильтруем по tender_type - обрабатываем только соответствующий тип
            entry_tender_type = entry.get("tender_type", "new")
            if entry_tender_type != tender_type:
                continue
            tender = {
                "id": entry["tender_id"],
                "registry_type": entry["registry_type"],
                "folder_path": entry["folder_path"],
            }
            
            # Проверяем кэш перед обработкой
            key = (tender["id"], tender["registry_type"])
            if key in processed_tenders_cache:
                match_result = processed_tenders_cache[key]
                self.tender_processor._log_already_processed(tender["id"], tender["registry_type"], match_result)
                self._processed_tenders.add(key)
                continue
            
            documents = self._safe_tender_call(
                self.tender_provider.get_tender_documents,
                tender["id"],
                tender["registry_type"],
            )
            # Определяем tender_type из папки
            tender_type_from_folder = entry.get("tender_type", "new")
            folder_path = self.folder_manager.prepare_tender_folder(tender["id"], tender["registry_type"], tender_type_from_folder)
            existing_records = self.existing_processor.build_records(folder_path)
            if not existing_records:
                continue
            tender["folder_path"] = folder_path
            result = self._process_tender(
                tender,
                documents=documents,
                existing_records=existing_records,
                processed_tenders_cache=processed_tenders_cache,
                tender_type=tender_type_from_folder,
            )
            if result:
                processed += 1
                self._processed_tenders.add((tender["id"], tender["registry_type"]))
        return processed

    def _process_tender(
        self,
        tender: Dict[str, Any],
        documents: Optional[List[Dict[str, Any]]] = None,
        existing_records: Optional[List[Dict[str, Any]]] = None,
        prefetched_data: Optional[PrefetchedTenderData] = None,
        processed_tenders_cache: Optional[Dict[Tuple[int, str], Dict[str, Any]]] = None,
        tender_type: str = 'new',
    ) -> Optional[Dict[str, Any]]:
        """Обработка одного тендера (делегируется TenderProcessor)"""
        tender_id = tender.get("id")
        registry_type = tender.get("registry_type", "44fz")
        folder_path = prefetched_data.folder_path if prefetched_data else self.folder_manager.prepare_tender_folder(tender_id, registry_type, tender_type)
        tender["folder_path"] = folder_path

        return self.tender_processor.process_tender(
            tender=tender,
            documents=documents,
            existing_records=existing_records,
            prefetched_data=prefetched_data,
            processed_tenders_cache=processed_tenders_cache,
            tender_type=tender_type,
            get_tender_documents_func=lambda tid, rt: self._safe_tender_call(
                self.tender_provider.get_tender_documents,
                tid,
                rt,
            ),
        )

    def _get_tender_documents_safe(self, tender_id: int, registry_type: str) -> List[Dict[str, Any]]:
        """Обертка для безопасного получения документов торга."""
        return self._safe_tender_call(
                self.tender_provider.get_tender_documents,
                tender_id,
                registry_type,
            )

    def _prepare_tenders_with_sizes(
        self,
        tenders: List[Dict[str, Any]],
        prefetcher: Optional[TenderPrefetcher],
        tender_type: str = 'new',
    ) -> Tuple[List[Tuple[Dict[str, Any], int]], Dict[int, int]]:
        """
        Подготавливает список тендеров с размерами папок и сортирует по размеру (от меньшего к большему).
        
        Args:
            tenders: Список тендеров для обработки
            prefetcher: Префетчер для скачивания документов (если есть)
            tender_type: Тип торгов ('new' или 'won')
            
        Returns:
            Кортеж из:
            - Список кортежей (tender, folder_size), отсортированный по размеру папки
            - Словарь маппинга id(tender) -> original_index для получения prefetched_data
        """
        if not tenders:
            return []
        
        logger.info("📦 Определение размеров папок для приоритизации обработки...")
        
        # Дожидаемся скачивания документов для всех тендеров через prefetcher
        if prefetcher:
            logger.info(f"Ожидание завершения скачивания документов для {len(tenders)} тендеров...")
            # Получаем prefetched_data для всех тендеров, чтобы дождаться скачивания
            for idx, tender in enumerate(tenders):
                try:
                    prefetcher.get_prefetched_data(idx, tender)
                except Exception as e:
                    logger.debug(f"Ошибка при получении prefetched_data для торга {tender.get('id')}: {e}")
        
        # Определяем размеры папок для всех тендеров и сохраняем маппинг оригинальных индексов
        tenders_with_sizes: List[Tuple[Dict[str, Any], int]] = []
        original_index_map: Dict[int, int] = {}  # id(tender) -> original_index
        
        for original_index, tender in enumerate(tenders):
            tender_id = tender.get("id")
            registry_type = tender.get("registry_type", "44fz")
            folder_path = self.folder_manager.prepare_tender_folder(tender_id, registry_type, tender_type)
            folder_size = self.folder_manager.get_folder_size(folder_path)
            tenders_with_sizes.append((tender, folder_size))
            
            # Сохраняем маппинг для получения prefetched_data
            original_index_map[id(tender)] = original_index
            
            # Логируем размер для отладки
            size_mb = folder_size / (1024 * 1024)
            logger.debug(f"Торг {tender_id} ({registry_type}): размер папки {size_mb:.2f} МБ")
        
        # Сортируем по размеру папки (от меньшего к большему)
        tenders_with_sizes.sort(key=lambda x: x[1])
        
        # Логируем статистику
        if tenders_with_sizes:
            min_size_mb = tenders_with_sizes[0][1] / (1024 * 1024)
            max_size_mb = tenders_with_sizes[-1][1] / (1024 * 1024)
            avg_size_mb = sum(size for _, size in tenders_with_sizes) / len(tenders_with_sizes) / (1024 * 1024)
            logger.info(
                f"✅ Приоритизация завершена: {len(tenders_with_sizes)} тендеров, "
                f"размеры от {min_size_mb:.2f} МБ до {max_size_mb:.2f} МБ (средний: {avg_size_mb:.2f} МБ)"
            )
            logger.info("📋 Обработка будет выполняться от меньших папок к большим для быстрого наполнения БД")
        
        return tenders_with_sizes, original_index_map

    def _create_prefetcher(self, tender_type: str = 'new') -> TenderPrefetcher:
        """Создает настроенный префетчер для фоновой загрузки документов."""
        prefetch_size = min(3, max(1, self.max_workers // 2))
        return TenderPrefetcher(
            folder_manager=self.folder_manager,
            selector=self.selector,
            downloader=self.downloader,
            max_prefetch=prefetch_size,
            tender_type=tender_type,
        )


    def _safe_tender_call(self, func, *args, **kwargs):
        while True:
            try:
                self._ensure_tender_connection()
                return func(*args, **kwargs)
            except DatabaseConnectionError as error:
                self._handle_db_disconnect(error)

    def _ensure_tender_connection(self):
        if self.tender_db_manager.is_connected():
            return
        self._attempt_connect()

    def _attempt_connect(self):
        try:
            self.tender_db_manager.connect()
        except DatabaseConnectionError as error:
            self._handle_db_disconnect(error)

    def _get_average_processing_time_per_file(self) -> float:
        """
        Получает среднее время обработки одного файла из истории БД.
        
        Returns:
            Среднее время обработки одного файла в секундах, или 0.0 если данных нет
        """
        try:
            from psycopg2.extras import RealDictCursor
            query = """
                SELECT 
                    AVG(processing_time_seconds / NULLIF(total_files_processed, 0)) as avg_time_per_file
                FROM tender_document_matches
                WHERE processing_time_seconds IS NOT NULL 
                    AND total_files_processed > 0
                    AND processing_time_seconds > 0
            """
            results = self.tender_db_manager.execute_query(query, None, RealDictCursor)
            if results and results[0].get('avg_time_per_file'):
                avg_time = float(results[0]['avg_time_per_file'])
                logger.debug(f"Среднее время обработки одного файла из истории: {avg_time:.2f} сек")
                return avg_time
        except Exception as error:
            logger.debug(f"Не удалось получить среднее время обработки из БД: {error}")
        
        return 0.0
    
    def _get_average_processing_time_per_tender(self) -> float:
        """
        Получает среднее время обработки одного торга из истории БД.
        
        Returns:
            Среднее время обработки одного торга в секундах, или 0.0 если данных нет
        """
        try:
            from psycopg2.extras import RealDictCursor
            query = """
                SELECT 
                    AVG(processing_time_seconds) as avg_time_per_tender
                FROM tender_document_matches
                WHERE processing_time_seconds IS NOT NULL 
                    AND processing_time_seconds > 0
            """
            results = self.tender_db_manager.execute_query(query, None, RealDictCursor)
            if results and results[0].get('avg_time_per_tender'):
                avg_time = float(results[0]['avg_time_per_tender'])
                logger.debug(f"Среднее время обработки одного торга из истории: {avg_time:.2f} сек")
                return avg_time
        except Exception as error:
            logger.debug(f"Не удалось получить среднее время обработки торга из БД: {error}")
        
        return 0.0
    
    @staticmethod
    def _format_eta(seconds: float) -> str:
        """Форматирует время в читаемый формат."""
        if seconds < 60:
            return f"{int(seconds)} сек"
        if seconds < 3600:
            minutes = int(seconds / 60)
            sec = int(seconds % 60)
            return f"{minutes} мин {sec} сек"
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours} ч {minutes} мин"
    
    def _handle_db_disconnect(self, error: Exception):
        logger.error(f"Потеряно подключение к БД tender_monitor: {error}")
        try:
            self.tender_db_manager.disconnect()
        except Exception:
            pass

        while True:
            logger.info(f"Повторное подключение к БД через {self._reconnect_delay} секунд...")
            time.sleep(self._reconnect_delay)
            try:
                self.tender_db_manager.connect()
                logger.info("Подключение к БД tender_monitor восстановлено")
                break
            except DatabaseConnectionError as reconnect_error:
                logger.error(f"Не удалось подключиться к БД tender_monitor: {reconnect_error}")
                continue

