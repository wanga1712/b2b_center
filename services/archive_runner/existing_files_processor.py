"""
Модуль для обработки уже существующих файлов в директории проектов.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List
import re

from loguru import logger


class ExistingFilesProcessor:
    """Обработчик ранее скачанных файлов в директории проектов."""

    FOLDER_PATTERN = re.compile(r"^(?P<registry>44fz|223fz)_(?P<tender_id>\d+)$", re.IGNORECASE)
    ARCHIVE_EXTENSIONS = {".rar", ".zip", ".7z"}
    EXCEL_EXTENSIONS = {".xlsx", ".xls"}

    def __init__(self, download_dir: Path):
        self.download_dir = Path(download_dir)

    def list_pending_tenders(self) -> List[Dict[str, Path]]:
        """
        Возвращает список директорий с проектами, в которых есть файлы для обработки.
        """
        pending: List[Dict[str, Path]] = []
        if not self.download_dir.exists():
            return pending

        for entry in self.download_dir.iterdir():
            if not entry.is_dir():
                continue
            match = self.FOLDER_PATTERN.match(entry.name)
            if not match:
                continue
            tender_id = int(match.group("tender_id"))
            registry_type = match.group("registry").lower()
            if self._folder_contains_documents(entry):
                pending.append(
                    {
                        "folder_path": entry,
                        "tender_id": tender_id,
                        "registry_type": registry_type,
                    }
                )
        logger.info(f"Найдено директорий с существующими файлами: {len(pending)}")
        return pending

    def build_records(self, folder: Path) -> List[Dict[str, List[Path]]]:
        """
        Собирает список записей (архивы/Excel) из существующей директории.
        """
        records: List[Dict[str, List[Path]]] = []
        if not folder.exists():
            return records

        for file_path in folder.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.name.startswith("~$"):
                continue
            suffix = file_path.suffix.lower()
            if suffix in self.ARCHIVE_EXTENSIONS or suffix in self.EXCEL_EXTENSIONS:
                records.append(
                    {
                        "doc": None,
                        "paths": [file_path],
                        "source": "existing",
                        "retries": 0,
                    }
                )
        logger.info(f"В папке {folder.name} найдено файлов для повторной обработки: {len(records)}")
        return records

    def _folder_contains_documents(self, folder: Path) -> bool:
        """
        Проверяет, есть ли в папке документы с поддерживаемыми расширениями.
        """
        for file_path in folder.rglob("*"):
            if not file_path.is_file():
                continue
            suffix = file_path.suffix.lower()
            if suffix in self.ARCHIVE_EXTENSIONS or suffix in self.EXCEL_EXTENSIONS:
                return True
        return False

