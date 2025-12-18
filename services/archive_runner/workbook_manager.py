"""
Менеджер подготовки документов для обработки.

Координирует работу с файлами, архивами и Excel файлами.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

from services.document_search.document_selector import DocumentSelector
from services.document_search.archive_extractor import ArchiveExtractor
from services.document_search.document_downloader import DocumentDownloader
from services.archive_runner.file_deduplicator import add_file_to_dict
from services.archive_runner.excel_preparator import ExcelPreparator
from services.archive_runner.archive_processor import ArchiveProcessor


class WorkbookManager:
    """Отвечает за распаковку архивов и подготовку путей к документам."""

    ARCHIVE_EXTENSIONS = {".rar", ".zip", ".7z"}
    EXCEL_EXTENSIONS = {".xlsx", ".xls"}
    WORD_EXTENSIONS = {".docx", ".doc"}
    PDF_EXTENSIONS = {".pdf"}

    def __init__(
        self,
        selector: DocumentSelector,
        extractor: ArchiveExtractor,
        downloader: Optional[DocumentDownloader] = None,
    ):
        self.selector = selector
        self.extractor = extractor
        self.downloader = downloader
        self._excel_preparator = ExcelPreparator()
        self._archive_processor = ArchiveProcessor(selector, extractor, downloader)

    def prepare_workbook_paths(
        self,
        records: List[Dict[str, Any]],
        documents: Optional[List[Dict[str, Any]]],
        tender_folder: Path,
    ) -> tuple[List[Path], List[Path], List[Path]]:
        """Возвращает списки подготовленных путей."""
        workbook_paths_dict: Dict[Tuple[str, int], Path] = {}
        workbook_paths_set: Set[Path] = set()
        archive_paths: List[Path] = []
        queue: List[Dict[str, Any]] = [self._normalize_record(record) for record in records]
        duplicates_count = 0

        while queue:
            record = queue.pop(0)
            for file_path in record["paths"]:
                path = Path(file_path).resolve()
                if not path.exists():
                    continue
                
                # Сначала определяем, является ли файл архивом (по расширению ИЛИ по содержимому)
                suffix = path.suffix.lower()
                is_archive = suffix in self.ARCHIVE_EXTENSIONS
                
                # Если расширение не архивное, но файл может быть архивом - проверяем содержимое
                if not is_archive and self.extractor.is_file_archive(path):
                    logger.info(f"Файл {path.name} имеет расширение {suffix}, но является архивом. Обрабатываем как архив.")
                    is_archive = True
                
                if is_archive:
                    # Это архив - распаковываем
                    archive_paths.append(path)
                    success = self._archive_processor.process_archive_path(
                        path,
                        record,
                        documents,
                        tender_folder,
                        queue,
                        workbook_paths_dict,
                        workbook_paths_set,
                    )
                    if not success:
                        logger.warning(f"Архив {path.name} пропущен из-за ошибок")
                elif suffix in self.EXCEL_EXTENSIONS:
                    # Это Excel файл (не архив) - обрабатываем напрямую
                    if path.name.startswith("~$"):
                        continue
                    prepared_path = self._excel_preparator.prepare_excel_file(path, tender_folder)
                    if prepared_path:
                        duplicates_count += add_file_to_dict(
                            prepared_path, workbook_paths_dict, workbook_paths_set, "Excel"
                        )
                    else:
                        logger.warning(f"Excel файл {path.name} не удалось подготовить, пропускаем")
                elif suffix in self.PDF_EXTENSIONS:
                    # PDF файлы добавляем напрямую (без копирования)
                    duplicates_count += add_file_to_dict(
                        path, workbook_paths_dict, workbook_paths_set, "PDF"
                    )
                elif suffix in self.WORD_EXTENSIONS:
                    # Word файлы добавляем напрямую (без копирования)
                    duplicates_count += add_file_to_dict(
                        path, workbook_paths_dict, workbook_paths_set, "Word"
                    )
                else:
                    logger.debug(f"Пропуск неподдерживаемого файла {path.name} (расширение: {suffix})")

        workbook_paths = list(workbook_paths_dict.values())
        if duplicates_count > 0:
            logger.info(
                f"Дедупликация файлов: найдено {duplicates_count} дубликатов, "
                f"уникальных {len(workbook_paths)}"
            )
        else:
            logger.info(f"Подготовлено уникальных документов для обработки: {len(workbook_paths)}")

        return workbook_paths, archive_paths, workbook_paths.copy()

    @staticmethod
    def _normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормализует запись для обработки.
        
        Args:
            record: Запись с метаданными
            
        Returns:
            Нормализованная запись
        """
        normalized = dict(record)
        normalized["paths"] = [Path(p) for p in record.get("paths", [])]
        normalized["retries"] = record.get("retries", 0)
        return normalized

