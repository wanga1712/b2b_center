"""
Сервис для скачивания документации торгов и поиска товаров внутри Excel-файлов.

Рефакторенная версия с разделением на модули.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger

from core.database import DatabaseManager
from core.exceptions import DocumentSearchError
from services.helpers.archive_cleanup import ArchiveCleanupManager
from services.document_search.document_downloader import DocumentDownloader
from services.document_search.document_selector import DocumentSelector
from services.document_search.archive_extractor import ArchiveExtractor
from services.document_search.match_finder import MatchFinder


class DocumentSearchService:
    """
    Сервис поиска информации в документации торгов.
    
    Координирует работу модулей:
    - DocumentSelector - выбор документов
    - DocumentDownloader - загрузка документов
    - ArchiveExtractor - извлечение архивов
    - MatchFinder - поиск совпадений
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        download_dir: Path,
        unrar_path: Optional[str] = None,
        winrar_path: Optional[str] = None,
        cleanup_manager: Optional[ArchiveCleanupManager] = None,
        progress_callback: Optional[callable] = None,
    ):
        """
        Args:
            db_manager: Менеджер БД с таблицей products
            download_dir: Директория для сохранения файлов
            unrar_path: Путь к инструменту UnRAR (опционально)
            winrar_path: Путь к директории WinRAR (опционально)
            cleanup_manager: Менеджер очистки временных файлов
            progress_callback: Функция для обновления прогресса (stage, progress, detail)
        """
        self.db_manager = db_manager
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self._product_names: Optional[List[str]] = None
        self.cleanup_manager = cleanup_manager or ArchiveCleanupManager()
        self.progress_callback = progress_callback

        self._downloader = DocumentDownloader(self.download_dir, progress_callback)
        self._selector = DocumentSelector()
        self._extractor = ArchiveExtractor(unrar_path, winrar_path)

    def _update_progress(self, stage: str, progress: int, detail: Optional[str] = None):
        """Обновление прогресса через callback"""
        if self.progress_callback:
            try:
                self.progress_callback(stage, progress, detail)
            except Exception as error:
                logger.debug(f"Ошибка при обновлении прогресса: {error}")

    def ensure_products_loaded(self) -> None:
        """Ленивая загрузка названий товаров (по требованию пользователя)."""
        if self._product_names is not None:
            return

        logger.info("Загрузка списка товаров для поиска по документации...")
        query = "SELECT name FROM products WHERE name IS NOT NULL"
        results = self.db_manager.execute_query(query)
        self._product_names = [row.get("name", "").strip() for row in results if row.get("name")]
        logger.info(f"Получено наименований товаров: {len(self._product_names)}")

    def run_document_search(
        self,
        documents: List[Dict[str, Any]],
        tender_id: Optional[int] = None,
        registry_type: str = "44fz",
    ) -> Dict[str, Any]:
        """
        Основной сценарий: найти документы, скачать и выполнить поиск.

        Args:
            documents: Метаданные документов торга
            tender_id: ID торга для создания папки
            registry_type: Тип реестра (44fz/223fz)

        Returns:
            Словарь с путем к файлу и найденными совпадениями
        """
        if not documents:
            raise DocumentSearchError("У выбранного торга нет приложенных документов.")

        self._update_progress("Подготовка...", 0, "Выбор документов для обработки")
        tender_folder = self._prepare_tender_folder(tender_id, registry_type)

        target_docs = self._selector.choose_documents(documents)
        unique_docs_to_download = self._selector.group_documents_by_archive(target_docs, documents)
        logger.info(f"Найдено уникальных документов/архивов для скачивания: {len(unique_docs_to_download)}")
        
        # ЭТАП 1: Скачивание документов
        total_to_download = len(unique_docs_to_download)
        self._update_progress("Скачивание документов", 0, f"Найдено документов для скачивания: {total_to_download}")
        logger.info(f"Начинаю параллельное скачивание {total_to_download} документов/архивов")
        
        all_downloaded_paths: List[Path] = []
        downloaded_count = 0
        with ThreadPoolExecutor(max_workers=min(4, total_to_download)) as executor:
            future_to_doc = {
                executor.submit(
                    self._downloader.download_required_documents,
                    target_doc,
                    documents,
                    tender_folder,
                ): target_doc
                for target_doc in unique_docs_to_download
            }
            
            for future in as_completed(future_to_doc):
                target_doc = future_to_doc[future]
                doc_name = target_doc.get('file_name') or target_doc.get('document_links', 'unknown')
                try:
                    downloaded_paths = future.result(timeout=300)
                    all_downloaded_paths.extend(downloaded_paths)
                    downloaded_count += 1
                    progress = int((downloaded_count / total_to_download) * 30) if total_to_download > 0 else 0
                    self._update_progress(
                        "Скачивание документов",
                        progress,
                        f"Скачано: {downloaded_count}/{total_to_download} - {doc_name}"
                    )
                    logger.info(f"Успешно скачан документ/архив: {doc_name}")
                except Exception as error:
                    logger.error(f"Ошибка при скачивании документа {doc_name}: {error}")
                    continue
        
        if not all_downloaded_paths:
            raise DocumentSearchError("Не удалось скачать ни один документ.")
        
        self._update_progress("Скачивание документов", 30, f"Скачано документов: {downloaded_count}/{total_to_download}")
        
        # ЭТАП 2: Извлечение данных
        self._update_progress("Извлечение данных", 30, "Распаковка архивов и подготовка файлов...")
        workbook_paths = self._prepare_workbook_paths(all_downloaded_paths)
        self._update_progress("Извлечение данных", 60, f"Найдено файлов для обработки: {len(workbook_paths)}")
        
        # ЭТАП 3: Сверка с данными из БД
        self._update_progress("Сверка с данными из БД", 60, "Загрузка списка товаров...")
        self.ensure_products_loaded()
        matches = self._aggregate_matches_for_workbooks(workbook_paths)

        self._update_progress("Завершено", 100, f"Найдено совпадений: {len(matches)}")
        logger.info(f"Поиск по документации завершен, найдено совпадений: {len(matches)}")

        result = {
            "file_path": str(workbook_paths[0]) if workbook_paths else "",
            "matches": matches,
            "tender_folder": str(tender_folder),
            "downloaded_files": [str(path) for path in all_downloaded_paths],
            "extract_dirs": [str(path) for path in self._extractor.active_extract_dirs],
        }

        try:
            self.cleanup_manager.cleanup(
                all_downloaded_paths,
                self._extractor.active_extract_dirs,
                matches,
            )
        except Exception as cleanup_error:
            logger.warning(f"Не удалось очистить временные файлы: {cleanup_error}")

        return result

    def _prepare_tender_folder(
        self,
        tender_id: Optional[int],
        registry_type: Optional[str],
    ) -> Path:
        """Создает рабочую директорию для файлов торга."""
        if not tender_id:
            fallback_dir = self.download_dir / "tender_temp"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir

        safe_type = (registry_type or "tender").strip().lower() or "tender"
        folder_name = f"{safe_type}_{tender_id}"
        target_dir = self.download_dir / folder_name
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def _prepare_workbook_paths(self, downloaded_paths: List[Path]) -> List[Path]:
        """
        Определение путей ко всем Excel файлам (напрямую или после распаковки архива).
        """
        if not downloaded_paths:
            raise DocumentSearchError("Не удалось скачать документ.")

        all_workbook_paths: List[Path] = []
        archive_paths: List[Path] = []
        excel_paths: List[Path] = []
        
        for path in downloaded_paths:
            suffix = path.suffix.lower()
            if suffix in {".rar", ".zip", ".7z"}:
                archive_paths.append(path)
            elif suffix in {".xlsx", ".xls"}:
                if self._extractor.is_file_archive(path):
                    logger.warning(f"Файл {path.name} имеет расширение Excel, но является архивом. Пропускаем.")
                    continue
                excel_paths.append(path)
            else:
                logger.warning(f"Неподдерживаемый формат файла: {path.name} (расширение: {suffix})")
        
        if archive_paths:
            from services.document_search.document_selector import DocumentSelector
            selector = DocumentSelector()
            sorted_archive_paths = sorted(archive_paths, key=lambda p: (selector.split_archive_name(p.name)[0] or p.stem.casefold(), selector.split_archive_name(p.name)[1] or 0))
            
            archive_groups: Dict[str, List[Path]] = {}
            for path in sorted_archive_paths:
                base_name, _ = selector.split_archive_name(path.name)
                group_key = base_name or path.stem.casefold()
                if group_key not in archive_groups:
                    archive_groups[group_key] = []
                archive_groups[group_key].append(path)
            
            for group_paths in archive_groups.values():
                first_path = group_paths[0]
                suffix = first_path.suffix.lower()
                
                if suffix == ".rar":
                    archive_path = first_path
                    if len(group_paths) > 1:
                        logger.info(
                            "Обнаружен многочастный RAR (%s частей). Распаковываю, начиная с %s",
                            len(group_paths),
                            first_path.name,
                        )
                else:
                    archive_path = (
                        self._extractor.combine_multi_part_archive(group_paths)
                        if len(group_paths) > 1
                        else first_path
                    )
                extracted_paths = self._extractor.extract_archive(archive_path)
                all_workbook_paths.extend(extracted_paths)
        
        all_workbook_paths.extend(excel_paths)
        
        if not all_workbook_paths:
            raise DocumentSearchError("Не найдено ни одного Excel файла для обработки.")
        
        logger.info(f"Подготовлено {len(all_workbook_paths)} файлов для парсинга")
        return all_workbook_paths

    def _aggregate_matches_for_workbooks(self, workbook_paths: List[Path]) -> List[Dict[str, Any]]:
        """Выполняет поиск по всем Excel и объединяет совпадения."""
        if not self._product_names:
            self.ensure_products_loaded()
        
        finder = MatchFinder(self._product_names)
        best_matches: Dict[str, Dict[str, Any]] = {}
        total_files = len(workbook_paths)
        
        for idx, workbook_path in enumerate(workbook_paths):
            progress = 60 + int(((idx + 1) / total_files) * 35) if total_files > 0 else 60
            file_name = workbook_path.name
            self._update_progress(
                "Сверка с данными из БД",
                progress,
                f"Обработка файла {idx + 1}/{total_files}: {file_name}"
            )
            
            logger.info(f"Поиск по документу: {workbook_path}")
            matches = finder.search_workbook_for_products(workbook_path)
            for match in matches:
                product_name = match["product_name"]
                existing = best_matches.get(product_name)
                if existing and existing["score"] >= match["score"]:
                    continue
                best_matches[product_name] = {
                    **match,
                    "source_file": str(workbook_path),
                }

        self._update_progress("Сверка с данными из БД", 95, f"Обработка завершена, найдено совпадений: {len(best_matches)}")
        
        sorted_matches = sorted(best_matches.values(), key=lambda item: item["score"], reverse=True)
        return sorted_matches[:50]

