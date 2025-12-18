"""
Вспомогательный модуль для предварительной проверки Excel файлов.

ExcelFileTester пытается открыть документ тем же ExcelParser,
что и основной поиск, чтобы заранее поймать проблемы с форматом.
Логика идентична тестовому скрипту: определяем формат,
читаем ограниченное число ячеек и логируем результат.
"""

from __future__ import annotations

from pathlib import Path
from typing import Set

from loguru import logger

from services.document_search.excel_parser import ExcelParser
from services.document_search.file_format_detector import detect_file_format


class ExcelFileTester:
    """Проверка Excel файла перед анализом."""

    def __init__(self, max_cells: int = 50):
        self.max_cells = max_cells
        self._parser = ExcelParser()

    def verify(self, file_path: Path) -> bool:
        """
        Быстрый прогон по файлу: читаем до max_cells ячеек и убеждаемся,
        что документ корректно открывается.
        """
        if not file_path.exists():
            logger.error(f"Файл {file_path} не существует, пропускаем проверку")
            return False

        detected_format = detect_file_format(file_path)
        size_mb = file_path.stat().st_size / (1024 * 1024)
        logger.debug(
            f"Проверка Excel файла {file_path.name}: размер {size_mb:.2f} МБ, "
            f"определенный формат: {detected_format}"
        )

        cells_read = 0
        sheets_seen: Set[str] = set()

        try:
            for cell in self._parser.iter_workbook_cells(file_path):
                cells_read += 1
                sheet = cell.get("sheet_name", "unknown")
                sheets_seen.add(sheet)
                if cells_read >= self.max_cells:
                    break

            logger.debug(
                f"Файл {file_path.name} успешно прошел проверку: "
                f"прочитано {cells_read} ячеек, листов {len(sheets_seen)}"
            )
            return True
        except Exception as error:
            logger.error(
                f"Файл {file_path.name} не прошел проверку ExcelParser: {error}"
            )
            return False


