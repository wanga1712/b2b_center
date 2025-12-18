"""
Сервис для обработки архивов и форматирования результатов поиска.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Sequence, TYPE_CHECKING
import time
import re

from loguru import logger

from services.helpers.archive_cleanup import ArchiveCleanupManager

if TYPE_CHECKING:
    from services.document_search_service import DocumentSearchService


def format_number(value: str) -> str:
    """Форматирует числа с разделителями разрядов."""
    if not value:
        return value

    cleaned = value.strip().replace("\n", " ").replace("\r", " ")
    number_pattern = r"\d+(?:[.,]\d+)?"

    def _format(match: re.Match) -> str:
        num = match.group(0)
        separator = ""
        if "." in num:
            integer_part, decimal_part = num.split(".", 1)
            separator = "."
        elif "," in num:
            integer_part, decimal_part = num.split(",", 1)
            separator = ","
        else:
            integer_part, decimal_part = num, ""

        chunks = []
        for index, digit in enumerate(reversed(integer_part)):
            if index and index % 3 == 0:
                chunks.append(" ")
            chunks.append(digit)
        formatted_integer = "".join(reversed(chunks))
        return f"{formatted_integer}{separator}{decimal_part}" if decimal_part else formatted_integer

    return re.sub(number_pattern, _format, cleaned)


def find_archives_in_directory(directory: Path) -> Dict[str, List[Path]]:
    """Находит архивы в директории (включая подпапки) и группирует по базовому имени."""
    archives: Dict[str, List[Path]] = defaultdict(list)
    archive_extensions = {".rar", ".zip", ".7z"}

    if not directory.exists():
        logger.error(f"Директория не существует: {directory}")
        return archives

    for file_path in directory.rglob("*"):
        if not file_path.is_file():
            continue
        suffix = file_path.suffix.lower()
        if suffix not in archive_extensions:
            continue
        base_name = _extract_base_name(file_path.name)
        archives[base_name].append(file_path)

    for base_name in archives:
        archives[base_name].sort(key=lambda p: _extract_part_number(p.name))

    return archives


def _extract_base_name(filename: str) -> str:
    name_without_ext = Path(filename).stem
    patterns = [
        r"\.part\d+$",
        r"\.part\s*\d+$",
        r"[._-]\d+$",
    ]
    for pattern in patterns:
        match = re.search(pattern, name_without_ext, re.IGNORECASE)
        if match:
            return name_without_ext[: match.start()].strip("._-")
    return name_without_ext


def _extract_part_number(filename: str) -> int:
    name_without_ext = Path(filename).stem
    patterns = [
        r"\.part(\d+)$",
        r"\.part\s*(\d+)$",
        r"[._-](\d+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, name_without_ext, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0


@dataclass
class ArchiveGroupResult:
    base_name: str
    workbook_paths: List[Path]
    matches: List[Dict[str, Any]]
    extract_dirs: List[Path]
    processing_time: float
    total_size: float


class ArchiveProcessingService:
    """Повторно используемая логика обработки архивов."""

    def __init__(
        self,
        document_service: "DocumentSearchService",
        cleanup_manager: Optional[ArchiveCleanupManager] = None,
    ):
        self.document_service = document_service
        self.cleanup_manager = cleanup_manager or ArchiveCleanupManager()

    def process_archive_group(
        self,
        base_name: str,
        archive_paths: Sequence[Path],
    ) -> ArchiveGroupResult:
        """Обрабатывает одну группу архивов."""
        start = time.time()
        result = self.document_service.debug_process_local_archives(
            [str(path) for path in archive_paths]
        )
        workbook_paths = [Path(p) for p in result.get("workbook_paths", [])]
        matches = result.get("matches", [])
        extract_dirs = [Path(p) for p in result.get("extract_dirs", [])]

        total_size = 0.0
        for workbook in workbook_paths:
            if workbook.exists():
                total_size += workbook.stat().st_size

        processing_time = time.time() - start

        try:
            self.cleanup_manager.cleanup(
                archive_paths,
                extract_dirs,
                matches,
            )
        except Exception as error:
            logger.warning(f"Не удалось очистить файлы архива {base_name}: {error}")

        return ArchiveGroupResult(
            base_name=base_name,
            workbook_paths=workbook_paths,
            matches=matches,
            extract_dirs=extract_dirs,
            processing_time=processing_time,
            total_size=total_size,
        )

    @staticmethod
    def group_matches_by_score(matches: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Разбивает совпадения на блоки по точности."""
        groups = {"exact": [], "good": []}
        for match in matches:
            score = match.get("score", 0)
            if score >= 100:
                groups["exact"].append(match)
            elif score >= 85:
                groups["good"].append(match)
        return groups

    @staticmethod
    def build_display_chunks(match: Dict[str, Any], download_dir: Path) -> Dict[str, str]:
        """Формирует части текста для отображения результата."""
        file_info = ArchiveProcessingService._build_file_info(match, download_dir)
        summary_line = ArchiveProcessingService._build_summary_line(match)
        cell_text = ArchiveProcessingService._build_cell_text(match)

        return {
            "file_info": file_info,
            "summary": summary_line,
            "cell_text": cell_text,
        }
    
    @staticmethod
    def _build_file_info(match: Dict[str, Any], download_dir: Path) -> str:
        """Формирует информацию о файле"""
        source_file = Path(match.get("source_file", ""))
        try:
            relative_file = source_file.relative_to(download_dir)
        except ValueError:
            relative_file = source_file
        
        return (
            f"📄 {relative_file} | 📍 Лист: {match.get('sheet_name')} "
            f"({match.get('cell_address')})"
        )
    
    @staticmethod
    def _build_summary_line(match: Dict[str, Any]) -> str:
        """Формирует строку с суммарной информацией"""
        row_data = match.get("row_data") or {}
        field_configs = [
            ("количество", "📦", "Количество"),
            ("стоимость_единицы", "💰", "Стоимость единицы"),
            ("общая_стоимость", "💵", "Общая стоимость"),
        ]
        
        chunks = []
        for field_key, icon, default_name in field_configs:
            if field_key in row_data:
                info = row_data[field_key]
                chunks.append(
                    f"{icon} {info.get('name', default_name)} ({info.get('column', '?')}): "
                    f"{format_number(str(info.get('value')))}"
                )
        
        return " | ".join(chunks) if chunks else ""
    
    @staticmethod
    def _build_cell_text(match: Dict[str, Any]) -> str:
        """Формирует текст ячейки"""
        cell_text = match.get("matched_display_text") or match.get("matched_text") or ""
        cleaned_text = " ".join(str(cell_text).split())
        if len(cleaned_text) > 200:
            cleaned_text = f"{cleaned_text[:200]}..."
        return f"📝 Строка: {cleaned_text}"

