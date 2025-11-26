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


class ArchiveBackgroundRunner:
    """
    Координатор фоновой обработки документов:
    1. Обрабатывает уже скачанные файлы
    2. Скачивает новые документы
    3. Находит совпадения и сохраняет результаты
    """

    ARCHIVE_EXTENSIONS = {".rar", ".zip", ".7z"}
    EXCEL_EXTENSIONS = {".xlsx", ".xls"}

    def __init__(
        self,
        tender_db_manager: TenderDatabaseManager,
        product_db_manager: DatabaseManager,
        user_id: int = 1,
        max_workers: int = 8,
    ):
        self.tender_db_manager = tender_db_manager
        self.product_db_manager = product_db_manager
        self.user_id = user_id
        self.max_workers = max_workers

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
        self.match_finder = MatchFinder(self.document_search_service._product_names)
        self.file_cleaner = FileCleaner()
        self.existing_processor = ExistingFilesProcessor(download_dir)

        self._processed_tenders: Set[Tuple[int, str]] = set()
        self._reconnect_delay = 60

    def run(self, specific_tender_ids: Optional[List[Dict[str, Any]]] = None, registry_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Запуск полного цикла обработки:
        - сначала существующие файлы
        - затем новые торги из БД или конкретные закупки
        
        Args:
            specific_tender_ids: Список словарей с ключами 'id' и 'registry_type' для конкретных закупок
            registry_type: Тип реестра для фильтрации ('44fz' или '223fz'). Если None, обрабатываются оба.
        """
        logger.info("🚀 Запуск автоматической обработки документов торгов")
        logger.info("=" * 80)

        overall_start = time.time()
        existing_processed = self._process_existing_folders(registry_type=registry_type)

        # Если указаны конкретные закупки, используем их, иначе получаем по настройкам
        if specific_tender_ids:
            tenders = self._safe_tender_call(
                self.tender_provider.get_target_tenders,
                specific_tender_ids=specific_tender_ids,
                registry_type=registry_type
            )
        else:
            tenders = self._safe_tender_call(
                self.tender_provider.get_target_tenders,
                registry_type=registry_type
            )
        
        if not tenders:
            logger.warning("Нет торгов для обработки")

        processed = 0
        errors = 0
        total_matches = 0

        for tender in tenders:
            tender_id = tender.get("id")
            registry_type = tender.get("registry_type", "44fz")
            key = (tender_id, registry_type)
            if key in self._processed_tenders:
                logger.info(f"Торг {tender_id} ({registry_type}) уже был обработан, пропускаем")
                continue

            result = self._process_tender(tender)
            if result:
                processed += 1
                total_matches += result.get("match_count", 0)
                self._processed_tenders.add(key)
            else:
                errors += 1

        overall_time = time.time() - overall_start

        logger.info(f"\n{'='*80}")
        logger.info("📊 ИТОГОВАЯ СТАТИСТИКА")
        logger.info(f"{'='*80}")
        logger.info(f"📁 Обработано существующих директорий: {existing_processed}")
        logger.info(f"📦 Новых торгов: {len(tenders)}")
        logger.info(f"✅ Успешно обработано: {processed}")
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

    def _process_existing_folders(self, registry_type: Optional[str] = None) -> int:
        """Обрабатывает уже скачанные файлы в директориях."""
        entries = self.existing_processor.list_pending_tenders()
        logger.info(f"Найдено директорий с существующими файлами: {len(entries)}")
        processed = 0
        for entry in entries:
            if registry_type and entry.get("registry_type") != registry_type:
                continue
            tender = {
                "id": entry["tender_id"],
                "registry_type": entry["registry_type"],
                "folder_path": entry["folder_path"],
            }
            documents = self._safe_tender_call(
                self.tender_provider.get_tender_documents,
                tender["id"],
                tender["registry_type"],
            )
            existing_records = self.existing_processor.build_records(entry["folder_path"])
            if not existing_records:
                continue
            result = self._process_tender(
                tender,
                documents=documents,
                existing_records=existing_records,
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
    ) -> Optional[Dict[str, Any]]:
        tender_id = tender.get("id")
        registry_type = tender.get("registry_type", "44fz")
        tender_name = tender.get("auction_name", f"Торг #{tender_id}")
        folder_path: Path = tender.get("folder_path") or self._prepare_tender_folder(tender_id, registry_type)

        # Проверяем наличие записи в БД
        match_result = self._safe_tender_call(
            self.tender_match_repo.get_match_result,
            tender_id,
            registry_type,
        )
        
        # Если результат уже есть в БД, проверяем, нужно ли переобрабатывать
        if match_result:
            processed_at = match_result.get("processed_at")
            match_count = match_result.get("match_count", 0)
            total_files = match_result.get("total_files_processed", 0)
            
            logger.info(
                f"Торг {tender_id} ({registry_type}) уже обработан ранее: "
                f"найдено {match_count} совпадений в {total_files} файлах, "
                f"обработано {processed_at if processed_at else 'неизвестно'}"
            )
            
            # Проверяем, есть ли файлы на диске
            if folder_path.exists() and any(folder_path.iterdir()):
                # Если файлы есть и результат свежий, пропускаем обработку
                logger.info(
                    f"Пропускаем повторную обработку торга {tender_id} ({registry_type}) - "
                    f"результат уже есть в БД и файлы присутствуют на диске. "
                    f"Для принудительной переобработки удалите запись из БД или файлы из папки."
                )
                return {
                    "tender_id": tender_id,
                    "registry_type": registry_type,
                    "match_count": match_count,
                    "match_percentage": match_result.get("match_percentage", 0.0),
                    "skipped": True,
                    "reason": "already_processed"
                }
            else:
                # Если файлов нет, но результат есть - возможно, файлы были удалены
                logger.info(
                    f"Результат есть в БД, но файлы отсутствуют. "
                    f"Будет выполнена повторная обработка."
                )
        
        # Всегда очищаем папку перед началом обработки, если записи нет в БД
        # Это предотвращает ошибки при попытке открыть неполные файлы после прерванной загрузки
        if not match_result:
            logger.info(
                f"Записи в БД для торга {tender_id} ({registry_type}) нет. "
                f"Очищаем папку перед началом обработки."
            )
            self._clean_tender_folder_force(folder_path)
            # Не используем existing_records, если записи нет в БД
            existing_records = None

        if documents is None:
            documents = self._safe_tender_call(
                self.tender_provider.get_tender_documents,
                tender_id,
                registry_type,
            )

        download_records: List[Dict[str, Any]] = []
        if existing_records:
            logger.info(
                "Используем уже скачанные файлы для торга %s (%s): %s записей",
                tender_id,
                registry_type,
                len(existing_records),
            )
            download_records.extend(existing_records)

        if not download_records and documents:
            try:
                selected_docs = self.selector.choose_documents(documents)
                unique_docs = self.selector.group_documents_by_archive(selected_docs, documents)
                new_records = self._download_documents(unique_docs, documents, folder_path)
                download_records.extend(new_records)
            except DocumentSearchError as error:
                logger.warning(f"Для торга {tender_id} нет документов, подходящих под критерии: {error}")

        if not download_records:
            logger.warning(f"Нет файлов для обработки по торгу {tender_id}")
            return None

        logger.info(f"\n{'='*80}")
        logger.info(f"Обработка торга: {tender_name} (ID: {tender_id}, {registry_type})")
        logger.info(f"{'='*80}")

        processing_start = time.time()
        workbook_paths, archive_paths, excel_paths = self._prepare_workbook_paths(
            download_records,
            documents,
            folder_path,
        )
        if not workbook_paths:
            logger.warning(f"Не удалось подготовить Excel файлы для торга {tender_id}")
            return None

        matches = self._search_matches(workbook_paths)
        processing_elapsed = time.time() - processing_start
        result = self._save_results(
            tender_id,
            registry_type,
            matches,
            workbook_paths,
            processing_elapsed,
        )

        # Очистка файлов - ошибки не прерывают выполнение
        self.file_cleaner.cleanup_all_files(
            archive_paths,
            workbook_paths,
            extraction_success=True,
            db_save_success=result is not None,
        )

        return result

    def _download_documents(
        self,
        unique_docs: List[Dict[str, Any]],
        all_documents: List[Dict[str, Any]],
        tender_folder: Path,
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        if not unique_docs:
            return records

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(unique_docs))) as executor:
            future_to_doc = {
                executor.submit(
                    self.downloader.download_required_documents,
                    doc,
                    all_documents,
                    tender_folder,
                ): doc
                for doc in unique_docs
            }

            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    paths = future.result(timeout=300)
                except Exception as error:
                    logger.error(f"Ошибка скачивания документа {doc.get('file_name')}: {error}")
                    continue
                if paths:
                    records.append(
                        {
                            "doc": doc,
                            "paths": paths,
                            "source": "download",
                            "retries": 0,
                        }
                    )
        return records

    def _prepare_workbook_paths(
        self,
        records: List[Dict[str, Any]],
        documents: Optional[List[Dict[str, Any]]],
        tender_folder: Path,
    ) -> tuple[List[Path], List[Path], List[Path]]:
        """
        Подготовка путей к Excel файлам с дедупликацией.
        Удаляет дубликаты файлов, которые могут появиться при распаковке нескольких частей архива.
        Дедупликация идет по имени файла + размер, чтобы исключить одинаковые файлы из разных папок.
        """
        # Используем словарь для дедупликации: ключ = (имя_файла, размер), значение = путь
        workbook_paths_dict: Dict[Tuple[str, int], Path] = {}
        workbook_paths_set: Set[Path] = set()  # Дополнительный set для быстрой проверки по пути
        archive_paths: List[Path] = []
        queue: List[Dict[str, Any]] = [self._normalize_record(record) for record in records]
        duplicates_count = 0

        while queue:
            record = queue.pop(0)
            for file_path in record["paths"]:
                path = Path(file_path).resolve()  # Используем resolve() для нормализации пути
                if not path.exists():
                    continue
                suffix = path.suffix.lower()
                if suffix in self.ARCHIVE_EXTENSIONS:
                    archive_paths.append(path)
                    success = self._process_archive_path(
                        path,
                        record,
                        documents,
                        tender_folder,
                        queue,
                        workbook_paths_dict,  # Передаем dict для дедупликации
                        workbook_paths_set,   # И set для быстрой проверки
                    )
                    if not success:
                        logger.warning(f"Архив {path.name} пропущен из-за ошибок")
                elif suffix in self.EXCEL_EXTENSIONS:
                    if path.name.startswith("~$"):
                        continue
                    if self.extractor.is_file_archive(path):
                        logger.warning(f"Файл {path.name} выглядит как архив, пропускаем")
                        continue
                    
                    # Дедупликация по имени файла + размер
                    try:
                        file_size = path.stat().st_size
                        dedup_key = (path.name, file_size)
                        
                        # Проверяем, есть ли уже файл с таким именем и размером
                        if dedup_key in workbook_paths_dict:
                            duplicates_count += 1
                            existing_path = workbook_paths_dict[dedup_key]
                            logger.debug(
                                "Пропуск дубликата файла: %s (размер: %s байт). "
                                "Уже обрабатывается: %s",
                                path.name,
                                file_size,
                                existing_path
                            )
                        else:
                            workbook_paths_dict[dedup_key] = path
                            workbook_paths_set.add(path)
                    except OSError as error:
                        logger.warning(f"Не удалось получить размер файла {path}: {error}")
                        # Если не удалось получить размер, добавляем по пути
                        if path not in workbook_paths_set:
                            workbook_paths_set.add(path)
                            # Используем только имя для дедупликации
                            dedup_key = (path.name, 0)
                            workbook_paths_dict[dedup_key] = path
                else:
                    logger.debug("Пропуск неподдерживаемого файла %s", path.name)

        # Преобразуем dict в list для совместимости
        workbook_paths = list(workbook_paths_dict.values())
        
        if duplicates_count > 0:
            logger.info(
                f"Дедупликация файлов: найдено {duplicates_count} дубликатов (по имени и размеру), "
                f"уникальных файлов: {len(workbook_paths)}"
            )
        else:
            logger.info(f"Подготовлено уникальных Excel файлов для обработки: {len(workbook_paths)}")

        return workbook_paths, archive_paths, workbook_paths.copy()

    def _process_archive_path(
        self,
        archive_path: Path,
        record: Dict[str, Any],
        documents: Optional[List[Dict[str, Any]]],
        tender_folder: Path,
        queue: List[Dict[str, Any]],
        workbook_paths_dict: Dict[Tuple[str, int], Path],  # Dict для дедупликации по имени+размер
        workbook_paths_set: Set[Path],  # Set для быстрой проверки по пути
    ) -> bool:
        try:
            doc_meta = record.get("doc") or {}
            base_name, part_number = self.selector.split_archive_name(doc_meta.get("file_name") or archive_path.name)
            if part_number and part_number > 1:
                logger.debug(
                    "Пропускаем распаковку части %s (ожидается обработка вместе с первой частью)",
                    archive_path.name,
                )
                return True

            target_dir = self._resolve_extract_dir(record, tender_folder, archive_path, base_name)
            extracted_paths = self.extractor.extract_archive(archive_path, target_dir)
            if not extracted_paths:
                logger.warning(f"Архив {archive_path.name} не содержит Excel файлов")
            else:
                # Дедупликация по имени файла + размер
                new_files = 0
                duplicates = 0
                for extracted_path in extracted_paths:
                    path = Path(extracted_path).resolve()
                    if not path.exists():
                        continue
                    
                    try:
                        file_size = path.stat().st_size
                        dedup_key = (path.name, file_size)
                        
                        # Проверяем, есть ли уже файл с таким именем и размером
                        if dedup_key in workbook_paths_dict:
                            duplicates += 1
                            existing_path = workbook_paths_dict[dedup_key]
                            logger.debug(
                                "Пропуск дубликата из архива %s: %s (размер: %s байт). "
                                "Уже обрабатывается: %s",
                                archive_path.name,
                                path.name,
                                file_size,
                                existing_path
                            )
                        else:
                            workbook_paths_dict[dedup_key] = path
                            workbook_paths_set.add(path)
                            new_files += 1
                    except OSError as error:
                        logger.warning(f"Не удалось получить размер файла {path}: {error}")
                        # Если не удалось получить размер, добавляем по пути
                        if path not in workbook_paths_set:
                            workbook_paths_set.add(path)
                            dedup_key = (path.name, 0)
                            workbook_paths_dict[dedup_key] = path
                            new_files += 1
                
                logger.info(
                    f"Архив {archive_path.name} распакован: найдено файлов {len(extracted_paths)}, "
                    f"новых {new_files}, дубликатов {duplicates}"
                )
                record.setdefault("extracted", []).extend(extracted_paths)
            return True
        except Exception as error:
            logger.warning(f"Архив {archive_path.name} поврежден: {error}")
            self._remove_file(archive_path)
            doc_meta = record.get("doc")
            retries = record.get("retries", 0)
            if not doc_meta or retries >= 1 or not documents:
                logger.error(f"Повторная загрузка для {archive_path.name} невозможна")
                return False
            try:
                new_paths = self.downloader.download_required_documents(doc_meta, documents, tender_folder)
                if new_paths:
                    queue.append(
                        {
                            "doc": doc_meta,
                            "paths": new_paths,
                            "source": "re-download",
                            "retries": retries + 1,
                        }
                    )
                    logger.info(f"Архив {archive_path.name} перезагружен повторно")
            except Exception as retry_error:
                logger.error(f"Не удалось повторно скачать архив {archive_path.name}: {retry_error}")
                return False
        return True

    def _resolve_extract_dir(
        self,
        record: Dict[str, Any],
        tender_folder: Path,
        archive_path: Path,
        base_name: Optional[str] = None,
    ) -> Path:
        doc_meta = record.get("doc") or {}
        file_name = doc_meta.get("file_name")
        if base_name is None and file_name:
            base_name, _ = self.selector.split_archive_name(file_name)
        if base_name:
            sanitized = base_name.replace("/", "_")
            return tender_folder / f"extract_{sanitized}"
        return tender_folder / f"extract_{archive_path.stem}"

    def _search_matches(self, workbook_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Параллельный поиск совпадений в Excel файлах.
        Обрабатывает файлы в нескольких потоках для ускорения.
        """
        matches: Dict[str, Dict[str, Any]] = {}
        
        # Дополнительная дедупликация на случай, если дубликаты все же попали
        unique_paths = list({Path(p).resolve() for p in workbook_paths})
        total_files = len(unique_paths)
        duplicates_removed = len(workbook_paths) - total_files
        
        if total_files == 0:
            return []
        
        if duplicates_removed > 0:
            logger.warning(
                "Обнаружено %s дубликатов в списке файлов для обработки, "
                "будет обработано уникальных файлов: %s",
                duplicates_removed,
                total_files
            )
        else:
            logger.info(f"Начинаем обработку {total_files} уникальных файлов")
        
        # Используем ThreadPoolExecutor для параллельной обработки файлов
        # Каждый поток создает свой экземпляр MatchFinder для потокобезопасности
        max_workers = min(self.max_workers, total_files)
        
        def process_file(workbook_path: Path) -> Tuple[Path, List[Dict[str, Any]], Optional[Exception], float]:
            """Обработка одного файла в отдельном потоке."""
            import time
            start_time = time.time()
            # Создаем отдельный экземпляр MatchFinder для каждого потока
            # так как openpyxl не потокобезопасен
            thread_match_finder = MatchFinder(self.match_finder.product_names)
            try:
                file_matches = thread_match_finder.search_workbook_for_products(workbook_path)
                elapsed = time.time() - start_time
                return workbook_path, file_matches, None, elapsed
            except Exception as error:
                elapsed = time.time() - start_time
                return workbook_path, [], error, elapsed
        
        # Получаем среднюю статистику обработки из БД для оценки времени
        avg_time_per_file = self._get_average_processing_time_per_file()
        
        processed_count = 0
        failed_count = 0
        total_elapsed_time = 0.0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Запускаем обработку всех файлов параллельно
            future_to_path = {
                executor.submit(process_file, workbook_path): workbook_path
                for workbook_path in unique_paths
            }
            
            for future in as_completed(future_to_path):
                workbook_path = future_to_path[future]
                processed_count += 1
                try:
                    # Получаем размер файла для информации
                    file_size_mb = 0
                    try:
                        file_size_mb = workbook_path.stat().st_size / (1024 * 1024)
                    except OSError:
                        pass
                    
                    # Без таймаута - обрабатываем файл в любом случае
                    path, file_matches, error, elapsed_time = future.result()
                    total_elapsed_time += elapsed_time
                    
                    if error:
                        logger.error(
                            f"Ошибка при поиске по файлу {workbook_path.name} "
                            f"(размер: {file_size_mb:.2f} МБ, время: {elapsed_time:.1f} сек): {error}"
                        )
                        failed_count += 1
                    else:
                        # Предупреждение, если файл обрабатывался слишком долго
                        if elapsed_time > 120:  # Более 2 минут
                            logger.warning(
                                f"Файл {workbook_path.name} обрабатывался долго: {elapsed_time:.1f} сек "
                                f"(размер: {file_size_mb:.2f} МБ)"
                            )
                        
                        logger.info(
                            f"Поиск по документу {workbook_path.name} ({processed_count}/{total_files}) - "
                            f"найдено совпадений: {len(file_matches)}, время: {elapsed_time:.1f} сек, "
                            f"размер: {file_size_mb:.2f} МБ"
                        )
                        
                        # Объединяем результаты из всех файлов
                        for match in file_matches:
                            # Фильтруем только совпадения с оценкой >= 85 (100% и 85%)
                            if match.get("score", 0) < 85.0:
                                continue
                            product_name = match.get("product_name")
                            existing = matches.get(product_name)
                            if not existing or existing.get("score", 0) < match.get("score", 0):
                                matches[product_name] = {**match, "source_file": str(workbook_path)}
                    
                    # Вычисляем и выводим оставшееся время
                    remaining_files = total_files - processed_count
                    if remaining_files > 0:
                        # Используем среднее время из истории, если доступно, иначе среднее время уже обработанных файлов
                        if avg_time_per_file > 0:
                            estimated_time_per_file = avg_time_per_file
                        elif processed_count > 0:
                            estimated_time_per_file = total_elapsed_time / processed_count
                        else:
                            estimated_time_per_file = 10.0  # Дефолтное значение
                        
                        # Учитываем параллельность
                        estimated_time_per_file_adjusted = estimated_time_per_file / max_workers
                        estimated_remaining_seconds = remaining_files * estimated_time_per_file_adjusted
                        
                        # Форматируем время
                        if estimated_remaining_seconds < 60:
                            time_str = f"{int(estimated_remaining_seconds)} сек"
                        elif estimated_remaining_seconds < 3600:
                            minutes = int(estimated_remaining_seconds / 60)
                            seconds = int(estimated_remaining_seconds % 60)
                            time_str = f"{minutes} мин {seconds} сек"
                        else:
                            hours = int(estimated_remaining_seconds / 3600)
                            minutes = int((estimated_remaining_seconds % 3600) / 60)
                            time_str = f"{hours} ч {minutes} мин"
                        
                        logger.info(
                            f"Прогресс: обработано {processed_count}/{total_files} файлов, "
                            f"осталось примерно {time_str}"
                        )
                            
                except Exception as error:
                    failed_count += 1
                    logger.error(
                        f"Ошибка при обработке файла {workbook_path.name}: {error}"
                    )
                    continue
        
        logger.info(
            f"Обработка файлов завершена: успешно {processed_count - failed_count}/{total_files}, "
            f"ошибок {failed_count}, найдено уникальных совпадений: {len(matches)}"
        )
        return list(matches.values())

    def _save_results(
        self,
        tender_id: int,
        registry_type: str,
        matches: List[Dict[str, Any]],
        workbook_paths: List[Path],
        processing_time: float,
    ) -> Optional[Dict[str, Any]]:
        exact_count = sum(1 for m in matches if m.get("score", 0) >= 100.0)
        good_count = sum(1 for m in matches if m.get("score", 0) >= 85.0)

        if exact_count > 0:
            match_percentage = 100.0
        elif good_count > 0:
            match_percentage = 85.0
        else:
            match_percentage = 0.0

        total_size = sum(path.stat().st_size for path in workbook_paths if path.exists())

        try:
            match_id = self._safe_tender_call(
                self.tender_match_repo.save_match_result,
                tender_id,
                registry_type,
                len(matches),
                match_percentage,
                processing_time,
                len(workbook_paths),
                total_size,
            )
            if not match_id:
                logger.error(f"❌ Не удалось сохранить итоговую запись для торга {tender_id}")
                return None

            # Сохраняем детали только если есть совпадения
            # Это предотвращает удаление существующих деталей при повторной обработке с пустым результатом
            if matches:
                self._safe_tender_call(
                    self.tender_match_repo.save_match_details,
                    match_id,
                    matches,
                )
            else:
                logger.debug(f"Нет совпадений для торга {tender_id}, детали не обновляются (сохраняются существующие)")

            logger.info(
                f"💾 tender_document_matches <- {{tender_id={tender_id}, registry={registry_type}, "
                f"matches={len(matches)}, files={len(workbook_paths)}, "
                f"size={total_size / (1024 * 1024) if total_size else 0:.2f} МБ}}"
            )
            logger.info(
                f"✅ Торг {tender_id} ({registry_type}) сохранен в БД: "
                f"совпадений {len(matches)}, процент {match_percentage} (match_id={match_id})"
            )
            return {
                "tender_id": tender_id,
                "registry_type": registry_type,
                "match_count": len(matches),
                "match_percentage": match_percentage,
            }
        except Exception as error:
            logger.error(f"❌ Ошибка записи результатов для торга {tender_id}: {error}")
            logger.exception("Детали ошибки:")
            return None

    def _prepare_tender_folder(self, tender_id: int, registry_type: str) -> Path:
        folder_name = f"{registry_type}_{tender_id}"
        target_dir = self.download_dir / folder_name
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def _clean_tender_folder(self, folder_path: Path) -> None:
        """
        Очищает все файлы в папке тендера, но не удаляет саму папку.
        Используется перед началом обработки, если записи нет в БД.
        """
        self._clean_tender_folder_force(folder_path)
    
    def _clean_tender_folder_force(self, folder_path: Path) -> None:
        """
        Принудительно очищает все файлы в папке тендера, убивая процессы, которые держат файлы.
        Используется при повторном запуске программы.
        """
        if not folder_path.exists() or not folder_path.is_dir():
            return
        
        logger.info(f"Принудительная очистка папки тендера: {folder_path}")
        deleted_count = 0
        failed_items = []
        
        for item in folder_path.iterdir():
            try:
                if item.is_file():
                    self._remove_file_force(item)
                    deleted_count += 1
                elif item.is_dir():
                    # Рекурсивно удаляем содержимое подпапок
                    try:
                        shutil.rmtree(item, ignore_errors=True)
                        deleted_count += 1
                    except Exception:
                        # Если не удалось удалить папку, пробуем принудительно удалить файлы внутри
                        self._remove_directory_force(item)
                        try:
                            item.rmdir()
                            deleted_count += 1
                        except Exception:
                            failed_items.append(str(item))
            except Exception as error:
                logger.warning(f"Не удалось удалить {item}: {error}")
                failed_items.append(str(item))
        
        if deleted_count > 0:
            logger.info(f"Удалено файлов/папок из {folder_path}: {deleted_count}")
        if failed_items:
            logger.warning(f"Не удалось удалить {len(failed_items)} элементов: {failed_items[:5]}")
    
    def _remove_directory_force(self, dir_path: Path) -> None:
        """Принудительно удаляет все файлы в директории."""
        try:
            for item in dir_path.rglob('*'):
                if item.is_file():
                    self._remove_file_force(item)
                elif item.is_dir():
                    try:
                        item.rmdir()
                    except Exception:
                        pass
        except Exception as error:
            logger.debug(f"Ошибка при принудительном удалении директории {dir_path}: {error}")
    
    def _remove_file_force(self, path: Path) -> None:
        """
        Принудительно удаляет файл, убивая процессы, которые его держат (только на Windows).
        """
        if not path.exists():
            return
        
        import sys
        import subprocess
        
        # Пробуем обычное удаление
        try:
            path.unlink()
            return
        except (OSError, PermissionError) as error:
            error_code = getattr(error, 'winerror', None) or getattr(error, 'errno', None)
            
            # WinError 32 = файл занят другим процессом
            if sys.platform == 'win32' and error_code == 32:
                try:
                    # На Windows используем handle.exe или PowerShell для поиска и убийства процесса
                    # Сначала пробуем через PowerShell
                    ps_command = f'''
                    $file = "{path}"; 
                    $processes = Get-Process | Where-Object {{$_.Path -eq $file -or (Get-Process -Id $_.Id).Modules.FileName -like "*$file*"}};
                    if ($processes) {{ $processes | Stop-Process -Force }}
                    '''
                    
                    subprocess.run(
                        ['powershell', '-Command', ps_command],
                        capture_output=True,
                        timeout=5,
                        check=False
                    )
                    
                    # Ждем немного и пробуем снова
                    import time
                    time.sleep(0.5)
                    
                    try:
                        path.unlink()
                        logger.debug(f"Файл {path.name} удален после завершения процесса")
                        return
                    except Exception:
                        pass
                except Exception as ps_error:
                    logger.debug(f"Не удалось завершить процесс через PowerShell: {ps_error}")
            
            # Если не помогло, пробуем переименовать и удалить позже
            try:
                temp_path = path.with_suffix(path.suffix + '.tmp_delete')
                if temp_path.exists():
                    temp_path.unlink()
                path.rename(temp_path)
                logger.debug(f"Файл {path.name} переименован для последующего удаления")
            except Exception:
                logger.warning(f"Не удалось принудительно удалить файл {path.name}")

    def _reset_tender_folder(self, folder_path: Path) -> None:
        """Полностью удаляет папку торга и создает заново."""
        try:
            if folder_path.exists():
                shutil.rmtree(folder_path, ignore_errors=False)
        except Exception as error:
            logger.warning(f"Не удалось полностью удалить папку {folder_path}: {error}")
        folder_path.mkdir(parents=True, exist_ok=True)


    def _normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(record)
        normalized["paths"] = [Path(p) for p in record.get("paths", [])]
        normalized["retries"] = record.get("retries", 0)
        return normalized

    def _remove_file(self, path: Path, max_retries: int = 3, retry_delay: float = 2.0) -> None:
        """
        Удаляет файл с повторными попытками и таймаутом.
        
        Args:
            path: Путь к файлу для удаления
            max_retries: Максимальное количество попыток
            retry_delay: Задержка между попытками в секундах
        """
        if not path.exists():
            return
        
        import time
        import os
        
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                # Пытаемся закрыть файл, если он открыт
                try:
                    if path.is_file():
                        # На Windows иногда помогает переименование перед удалением
                        temp_path = path.with_suffix(path.suffix + '.tmp')
                        if temp_path.exists():
                            temp_path.unlink()
                        path.rename(temp_path)
                        temp_path.unlink()
                    else:
                        path.unlink()
                except (OSError, PermissionError):
                    # Если переименование не помогло, пробуем обычное удаление
                    path.unlink()
                
                logger.debug(f"Удален файл: {path}")
                return
                
            except (OSError, PermissionError) as error:
                last_error = error
                error_code = getattr(error, 'winerror', None) or getattr(error, 'errno', None)
                
                # WinError 32 = файл занят другим процессом
                # errno 13 = Permission denied
                if error_code in (32, 13) and attempt < max_retries:
                    logger.debug(
                        f"Файл {path.name} занят другим процессом. "
                        f"Попытка {attempt}/{max_retries}, повтор через {retry_delay} сек..."
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    break
            except Exception as error:
                last_error = error
                break
        
        # Если все попытки не удались, логируем предупреждение
        logger.warning(
            f"Не удалось удалить файл {path.name} после {max_retries} попыток: {last_error}. "
            f"Файл будет удален позже автоматически."
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
    
    def _handle_db_disconnect(self, error: Exception):
        logger.error("Потеряно подключение к БД tender_monitor: %s", error)
        try:
            self.tender_db_manager.disconnect()
        except Exception:
            pass

        while True:
            logger.info("Повторное подключение к БД через %s секунд...", self._reconnect_delay)
            time.sleep(self._reconnect_delay)
            try:
                self.tender_db_manager.connect()
                logger.info("Подключение к БД tender_monitor восстановлено")
                break
            except DatabaseConnectionError as reconnect_error:
                logger.error("Не удалось подключиться к БД tender_monitor: %s", reconnect_error)
                continue

