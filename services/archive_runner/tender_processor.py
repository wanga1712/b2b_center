"""
Модуль обработки одного тендера.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from core.exceptions import DocumentSearchError
from services.document_search.document_selector import DocumentSelector
from services.document_search.document_downloader import DocumentDownloader
from services.document_search.archive_extractor import ArchiveExtractor
from services.document_search.match_finder import MatchFinder
from services.tender_match_repository import TenderMatchRepository
from services.archive_runner.tender_folder_manager import TenderFolderManager
from services.archive_runner.file_cleaner import FileCleaner
from services.archive_runner.tender_prefetcher import PrefetchedTenderData
from services.archive_runner.document_download_manager import DocumentDownloadManager
from services.archive_runner.workbook_manager import WorkbookManager
from services.archive_runner.match_executor import MatchExecutor
from services.archive_runner.result_saver import ResultSaver


class TenderProcessor:
    """Оркестратор полного цикла обработки одного тендера."""

    def __init__(
        self,
        tender_match_repo: TenderMatchRepository,
        folder_manager: TenderFolderManager,
        document_search_service,
        selector: DocumentSelector,
        downloader: DocumentDownloader,
        extractor: ArchiveExtractor,
        match_finder: MatchFinder,
        file_cleaner: FileCleaner,
        max_workers: int = 2,
        safe_call_func=None,
        get_avg_time_func=None,
        batch_delay: float = 5.0,
    ):
        self.folder_manager = folder_manager
        self.file_cleaner = file_cleaner
        self.selector = selector
        self.downloader = downloader
        self._safe_call = safe_call_func

        self.download_manager = DocumentDownloadManager(downloader, max_workers)
        self.workbook_manager = WorkbookManager(selector, extractor, downloader)
        # Передаем batch_delay для пауз между партиями файлов
        self.match_executor = MatchExecutor(match_finder, max_workers, get_avg_time_func, batch_delay)
        self.result_saver = ResultSaver(tender_match_repo, safe_call_func)

    def process_tender(
        self,
        tender: Dict[str, Any],
        documents: Optional[List[Dict[str, Any]]] = None,
        existing_records: Optional[List[Dict[str, Any]]] = None,
        get_tender_documents_func=None,
        prefetched_data: Optional[PrefetchedTenderData] = None,
        processed_tenders_cache: Optional[Dict] = None,
        tender_type: str = 'new',
    ) -> Optional[Dict[str, Any]]:
        """
        Обработка одного тендера.
        
        Returns:
            Dict с результатами обработки или None в случае критической ошибки
        """
        tender_id = tender.get("id")
        registry_type = tender.get("registry_type", "44fz")
        tender_name = tender.get("auction_name", f"Торг #{tender_id}")
        folder_path = prefetched_data.folder_path if prefetched_data else self.folder_manager.prepare_tender_folder(tender_id, registry_type, tender_type)
        tender["folder_path"] = folder_path

        # Блокировки advisory-lock отключены для параллельной обработки новых и разыгранных торгов
        # Новые и разыгранные торги обрабатываются независимо в разных процессах
        
        logger.debug(f"🔍 Начинаем обработку торга {tender_id} ({registry_type}, {tender_type})")

        # Используем кэш если доступен, иначе запрос к БД
        match_result = None
        if processed_tenders_cache:
            match_result = processed_tenders_cache.get((tender_id, registry_type))
        
        if not match_result:
            match_result = (
                self._safe_call(
                    self.result_saver.tender_match_repo.get_match_result,
                    tender_id,
                    registry_type,
                )
                if self._safe_call
                else self.result_saver.tender_match_repo.get_match_result(tender_id, registry_type)
            )
        
        if match_result:
            self._log_already_processed(tender_id, registry_type, match_result)
            return {
                "tender_id": tender_id,
                "registry_type": registry_type,
                "match_count": match_result.get("match_count", 0),
                "match_percentage": match_result.get("match_percentage", 0.0),
                "skipped": True,
                "reason": "already_processed",
            }

        # Проверяем существующие файлы на валидность (только если торг не обработан)
        # ВАЖНО: Проверка происходит ВСЕГДА, даже для prefetched файлов,
        # чтобы убедиться что они не повреждены и могут быть открыты/распакованы
        try:
            existing_records = None
            if prefetched_data and prefetched_data.download_records:
                # Если использовался prefetching, проверяем скачанные файлы на валидность
                # перед использованием (файлы могли быть повреждены при скачивании)
                logger.debug(f"Проверяем предзагруженные файлы для торга {tender_id} ({registry_type}) на валидность")
                valid_records = self._validate_prefetched_files(prefetched_data.download_records, folder_path)
                if valid_records is None:
                    # Все файлы повреждены - очищаем папку и скачиваем заново
                    logger.warning(f"Предзагруженные файлы для торга {tender_id} ({registry_type}) повреждены, очищаем папку и скачиваем заново")
                    self.folder_manager.clean_tender_folder_force(folder_path)
                    prefetched_data.download_records = []
                    existing_records = None
                elif len(valid_records) < len(prefetched_data.download_records):
                    # Некоторые файлы повреждены - удаляем их из списка
                    logger.warning(f"Некоторые предзагруженные файлы для торга {tender_id} ({registry_type}) повреждены, удаляем их из списка")
                    prefetched_data.download_records = valid_records
                    existing_records = valid_records
                else:
                    # Все файлы валидны
                    existing_records = valid_records
                    logger.info(f"Предзагруженные файлы для торга {tender_id} ({registry_type}) валидны, используем их")
            elif not (prefetched_data and prefetched_data.cleaned):
                # Если prefetching не использовался, проверяем существующие файлы в папке
                existing_records = self._check_existing_files(folder_path)
                if existing_records is None:
                    # Файлы повреждены - очищаем папку
                    logger.warning(f"Обнаружены поврежденные файлы в папке торга {tender_id} ({registry_type}), очищаем папку")
                    self.folder_manager.clean_tender_folder_force(folder_path)
                    existing_records = None
                elif existing_records:
                    logger.info(f"Найдены валидные файлы в папке торга {tender_id} ({registry_type}), используем их")

            documents = documents or (prefetched_data.documents if prefetched_data else None)
            if documents is None and get_tender_documents_func:
                documents = get_tender_documents_func(tender_id, registry_type)

            # Строим список записей для скачивания/использования
            # Если есть existing_records (валидные файлы), используем их
            # Иначе используем prefetched_data.download_records (если они есть и валидны)
            download_records = self._build_download_records(existing_records, prefetched_data)
            if not download_records and documents:
                try:
                    selected_docs = self.selector.choose_documents(documents)
                    unique_docs = self.selector.group_documents_by_archive(selected_docs, documents)
                    download_records = self.download_manager.download_documents(unique_docs, documents, folder_path)
                except DocumentSearchError as error:
                    logger.warning(f"Для торга {tender_id} нет подходящих документов: {error}")

            if not download_records:
                logger.warning(f"❌ Нет файлов для обработки по торгу {tender_id} ({registry_type}) - сохраняем ошибку в БД")
                # Сохраняем ошибку в БД для последующей ручной обработки
                processing_start = time.time()
                try:
                    error_result = self.result_saver.save(
                        tender_id,
                        registry_type,
                        [],
                        [],
                        time.time() - processing_start,
                        error_reason="no_documents",
                    )
                    logger.debug(f"Ошибка 'no_documents' сохранена в БД для торга {tender_id}: {error_result is not None}")
                except Exception as save_error:
                    logger.error(f"Не удалось сохранить ошибку 'no_documents' в БД для торга {tender_id}: {save_error}", exc_info=True)
                    error_result = None
                return {
                    "tender_id": tender_id,
                    "registry_type": registry_type,
                    "match_count": 0,
                    "match_percentage": 0.0,
                    "skipped": True,
                    "reason": "no_documents",
                    "error_saved": error_result is not None,
                }

            logger.info(f"\n{'=' * 80}")
            logger.info(f"Обработка торга: {tender_name} (ID: {tender_id}, {registry_type})")
            logger.info(f"{'=' * 80}")
            logger.info(f"Найдено записей для скачивания/использования: {len(download_records)}")
            
            # Детальное логирование для диагностики
            if download_records:
                total_files = sum(len(record.get("paths", [])) for record in download_records)
                logger.info(f"Всего файлов в записях: {total_files}")
                for idx, record in enumerate(download_records[:3]):  # Показываем первые 3 записи
                    paths = record.get("paths", [])
                    logger.debug(f"  Запись {idx+1}: {len(paths)} файлов, пути: {[str(p)[-50:] for p in paths[:2]]}")

            processing_start = time.time()
            logger.info(f"Подготовка путей к файлам для торга {tender_id}...")
            try:
                workbook_paths, archive_paths, excel_paths = self.workbook_manager.prepare_workbook_paths(
                    download_records,
                    documents,
                    folder_path,
                )
                logger.info(f"Подготовлено путей: workbook={len(workbook_paths) if workbook_paths else 0}, archive={len(archive_paths) if archive_paths else 0}, excel={len(excel_paths) if excel_paths else 0}")
            except Exception as prep_error:
                logger.error(f"❌ Ошибка при подготовке путей к файлам для торга {tender_id}: {prep_error}", exc_info=True)
                error_result = self.result_saver.save(
                    tender_id,
                    registry_type,
                    [],
                    [],
                    time.time() - processing_start,
                    error_reason=f"prepare_paths_error: {str(prep_error)[:200]}",
                )
                return {
                    "tender_id": tender_id,
                    "registry_type": registry_type,
                    "match_count": 0,
                    "match_percentage": 0.0,
                    "error": True,
                    "error_message": f"Ошибка подготовки путей: {prep_error}",
                    "error_saved": error_result is not None,
                }
            
            if not workbook_paths:
                logger.error(f"❌ Не удалось подготовить Excel файлы для торга {tender_id} ({registry_type})")
                logger.error(f"   download_records: {len(download_records)} записей")
                if download_records:
                    total_files = sum(len(record.get("paths", [])) for record in download_records)
                    logger.error(f"   Всего файлов в записях: {total_files}")
                    # Показываем детали первых записей
                    for idx, record in enumerate(download_records[:5]):
                        paths = record.get("paths", [])
                        logger.error(f"   Запись {idx+1}: {len(paths)} файлов")
                        for path_idx, path in enumerate(paths[:3]):
                            path_obj = Path(path)
                            exists = path_obj.exists()
                            logger.error(f"      Файл {path_idx+1}: {path_obj.name} (существует: {exists}, размер: {path_obj.stat().st_size if exists else 0})")
                logger.error(f"   Папка торга: {folder_path} (существует: {folder_path.exists()})")
                
                # Сохраняем ошибку в БД для последующей ручной обработки
                try:
                    error_result = self.result_saver.save(
                        tender_id,
                        registry_type,
                        [],
                        [],
                        time.time() - processing_start,
                        error_reason="no_workbook_files",
                    )
                    logger.debug(f"Ошибка 'no_workbook_files' сохранена в БД для торга {tender_id}: {error_result is not None}")
                except Exception as save_error:
                    logger.error(f"Не удалось сохранить ошибку 'no_workbook_files' в БД для торга {tender_id}: {save_error}", exc_info=True)
                    error_result = None
                return {
                    "tender_id": tender_id,
                    "registry_type": registry_type,
                    "match_count": 0,
                    "match_percentage": 0.0,
                    "skipped": True,
                    "reason": "no_workbook_files",
                    "error_message": f"Не удалось подготовить Excel файлы: {len(download_records)} записей, {sum(len(r.get('paths', [])) for r in download_records)} файлов",
                    "error_saved": error_result is not None,
                }
            
            logger.debug(f"Начинаем парсинг {len(workbook_paths)} файлов для торга {tender_id}...")

            try:
                logger.debug(f"Запуск match_executor.run() для торга {tender_id} с {len(workbook_paths)} файлами")
                matches = self.match_executor.run(workbook_paths)
                logger.debug(f"Match executor вернул {len(matches) if matches else 0} совпадений для торга {tender_id}")
                processing_elapsed = time.time() - processing_start
                logger.debug(f"Сохранение результатов в БД для торга {tender_id}...")
                result = self.result_saver.save(tender_id, registry_type, matches, workbook_paths, processing_elapsed)
                logger.debug(f"Result saver вернул для торга {tender_id}: {result}")

                # Показываем результат обработки
                match_count = len(matches) if matches else 0
                if match_count > 0:
                    logger.info(f"🔍 Найдено совпадений: {match_count} (время обработки: {processing_elapsed:.1f} сек)")
                else:
                    logger.info(f"⚠️ Совпадений не найдено (время обработки: {processing_elapsed:.1f} сек)")

                # Удаляем файлы только после успешной записи в БД (неблокирующее удаление)
                if result is not None:
                    logger.info(f"Результаты сохранены в БД для торга {tender_id}, удаляем файлы")
                    try:
                        self.file_cleaner.cleanup_all_files(
                            archive_paths,
                            workbook_paths,
                            extraction_success=True,
                            db_save_success=True,
                        )
                    except Exception as cleanup_error:
                        # Не блокируем процесс, если удаление не удалось
                        logger.warning(f"Не удалось удалить некоторые файлы для торга {tender_id}: {cleanup_error}")
                else:
                    # Если result_saver.save() вернул None, это ошибка сохранения в БД
                    logger.error(
                        f"❌ Не удалось сохранить результаты в БД для торга {tender_id} ({registry_type}). "
                        f"Найдено совпадений: {match_count}, но сохранение не удалось."
                    )
                    # Возвращаем словарь с информацией об ошибке вместо None
                    return {
                        "tender_id": tender_id,
                        "registry_type": registry_type,
                        "match_count": match_count,
                        "match_percentage": 0.0,
                        "error": True,
                        "error_message": "Не удалось сохранить результаты в БД",
                        "error_saved": False,
                    }
                
                return result
            except Exception as processing_error:
                processing_elapsed = time.time() - processing_start
                error_message = str(processing_error)
                logger.error(
                    f"❌ Ошибка при обработке торга {tender_id} ({registry_type}): {error_message}",
                    exc_info=True  # Добавляем полный traceback
                )
                # Сохраняем ошибку в БД для последующей ручной обработки
                error_result = self.result_saver.save(
                    tender_id,
                    registry_type,
                    [],
                    workbook_paths,
                    processing_elapsed,
                    error_reason=f"processing_error: {error_message[:200]}",  # Ограничиваем длину сообщения
                )
                return {
                    "tender_id": tender_id,
                    "registry_type": registry_type,
                    "match_count": 0,
                    "match_percentage": 0.0,
                    "error": True,
                    "error_message": error_message,
                    "error_saved": error_result is not None,
                }
        except Exception as critical_error:
            # Критическая ошибка на уровне всего метода - логируем с полным traceback
            logger.error(
                f"❌ КРИТИЧЕСКАЯ ошибка при обработке торга {tender_id} ({registry_type}): {critical_error}",
                exc_info=True
            )
            # Возвращаем None, чтобы runner знал, что произошла ошибка
            return None

    def _build_download_records(
        self,
        existing_records: Optional[List[Dict[str, Any]]],
        prefetched_data: Optional[PrefetchedTenderData],
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        if prefetched_data and prefetched_data.download_records:
            logger.info(
                f"Используем предзагруженные документы для торга {prefetched_data.tender_id} ({prefetched_data.registry_type})"
            )
            records.extend(prefetched_data.download_records)
        elif existing_records:
            logger.info(
                f"Используем ранее скачанные файлы для торга (кол-во: {len(existing_records)})"
            )
            records.extend(existing_records)
        return records

    def _validate_prefetched_files(self, download_records: List[Dict[str, Any]], folder_path: Path) -> Optional[List[Dict[str, Any]]]:
        """
        Проверяет предзагруженные файлы на валидность.
        
        Args:
            download_records: Список записей о скачанных файлах
            folder_path: Путь к папке торга
            
        Returns:
            List[Dict] если файлы валидны (может быть меньше чем исходный список, если некоторые повреждены)
            None если все файлы повреждены
        """
        if not download_records:
            return []
        
        valid_records = []
        for record in download_records:
            file_paths = record.get("paths", [])
            if not file_paths:
                continue
            
            record_valid = True
            for file_path in file_paths:
                path = Path(file_path)
                if not path.exists():
                    record_valid = False
                    break
                
                suffix = path.suffix.lower()
                is_valid = False
                
                # Проверяем архивы - пытаемся открыть
                if suffix in {".rar", ".zip", ".7z"}:
                    try:
                        if suffix == ".zip":
                            import zipfile
                            with zipfile.ZipFile(path, 'r') as zf:
                                zf.testzip()  # Проверка целостности
                            is_valid = True
                        elif suffix == ".rar":
                            # Для RAR проверяем что файл существует и не пустой
                            if path.stat().st_size > 0:
                                is_valid = True
                        elif suffix == ".7z":
                            # Для 7z проверяем что файл существует и не пустой
                            if path.stat().st_size > 0:
                                is_valid = True
                    except Exception:
                        is_valid = False
                # Проверяем Excel файлы - пытаемся открыть
                elif suffix in {".xlsx", ".xls"}:
                    try:
                        import openpyxl
                        if suffix == ".xlsx":
                            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
                            wb.close()
                            is_valid = True
                        else:
                            # Для .xls нужен xlrd, но пока просто проверяем размер
                            if path.stat().st_size > 0:
                                is_valid = True
                    except Exception:
                        is_valid = False
                
                if not is_valid:
                    record_valid = False
                    logger.warning(f"Файл {path.name} поврежден или не может быть открыт")
                    break
            
            if record_valid:
                valid_records.append(record)
        
        if not valid_records:
            return None
        
        return valid_records
    
    def _check_existing_files(self, folder_path: Path) -> Optional[List[Dict[str, Any]]]:
        """
        Проверяет существующие файлы в папке на валидность.
        
        Returns:
            List[Dict] если файлы валидны и могут быть использованы
            None если файлы повреждены и папку нужно очистить
            [] если файлов нет (но это не ошибка)
        """
        if not folder_path.exists():
            return []
        
        from services.archive_runner.existing_files_processor import ExistingFilesProcessor
        
        existing_processor = ExistingFilesProcessor(folder_path.parent)
        records = existing_processor.build_records(folder_path)
        
        if not records:
            return []
        
        # Проверяем каждый файл на валидность
        valid_records = []
        corrupted_files = []
        
        for record in records:
            file_paths = record.get("paths", [])
            if not file_paths:
                continue
            
            record_valid = True
            for file_path in file_paths:
                path = Path(file_path)
                if not path.exists():
                    continue
                
                suffix = path.suffix.lower()
                is_valid = False
                
                # Проверяем архивы - пытаемся открыть
                if suffix in {".rar", ".zip", ".7z"}:
                    try:
                        # Быстрая проверка - пытаемся открыть архив
                        if suffix == ".zip":
                            import zipfile
                            with zipfile.ZipFile(path, 'r') as zf:
                                zf.testzip()  # Проверка целостности
                            is_valid = True
                        elif suffix == ".7z":
                            import py7zr
                            with py7zr.SevenZipFile(path, mode='r') as archive:
                                archive.getnames()  # Проверка что архив читается
                            is_valid = True
                        # Для RAR проверка сложнее, считаем валидным если существует
                        elif suffix == ".rar":
                            is_valid = True
                    except Exception as error:
                        logger.warning(f"Архив {path.name} поврежден: {error}")
                        corrupted_files.append(path.name)
                        is_valid = False
                
                # Проверяем Excel файлы через тестер
                elif suffix in {".xlsx", ".xls"}:
                    if self.workbook_manager._excel_preparator._excel_tester.verify(path):
                        is_valid = True
                    else:
                        logger.warning(f"Excel файл {path.name} поврежден или не может быть открыт")
                        corrupted_files.append(path.name)
                        is_valid = False
                
                if not is_valid:
                    record_valid = False
                    break
            
            if record_valid:
                valid_records.append(record)
        
        # Если все файлы повреждены - возвращаем None (нужно очистить папку)
        if corrupted_files and not valid_records:
            logger.warning(f"Все файлы повреждены: {corrupted_files}")
            return None
        
        # Если есть хотя бы один валидный файл - используем их
        if valid_records:
            if corrupted_files:
                logger.warning(f"Некоторые файлы повреждены и будут пропущены: {corrupted_files}")
            return valid_records
        
        return []

    @staticmethod
    def _log_already_processed(tender_id: int, registry_type: str, match_result: Dict[str, Any]) -> None:
        logger.info(
            f"Торг {tender_id} ({registry_type}) уже обработан: совпадений {match_result.get('match_count', 0)}, файлов {match_result.get('total_files_processed', 0)}, обработано {match_result.get('processed_at') or 'неизвестно'}"
        )
        logger.info(
            f"Пропускаем повторную обработку торга {tender_id} ({registry_type}). Для переобработки удалите запись из tender_document_matches."
        )

