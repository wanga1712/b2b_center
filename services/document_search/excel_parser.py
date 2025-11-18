"""
Модуль для парсинга Excel файлов.

Класс ExcelParser отвечает за:
- Чтение .xlsx и .xls файлов
- Итерацию по ячейкам
- Извлечение данных из строк
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional
import re

from loguru import logger
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

try:
    import xlrd
    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False
    logger.warning("Библиотека xlrd не установлена. Поддержка старых .xls файлов будет недоступна.")

from core.exceptions import DocumentSearchError


class ExcelParser:
    """Класс для парсинга Excel файлов."""

    def iter_workbook_cells(self, file_path: Path) -> Iterable[Dict[str, Any]]:
        """
        Итерация по всем ячейкам Excel (XLSX или XLS) с информацией о позиции.
        
        Поддерживает оба формата:
        - .xlsx через openpyxl
        - .xls через xlrd
        """
        suffix = file_path.suffix.lower()
        
        if suffix == ".xls":
            if not XLRD_AVAILABLE:
                raise DocumentSearchError(
                    "Библиотека xlrd не установлена. "
                    "Установите её для поддержки .xls файлов: pip install xlrd"
                )
            
            try:
                workbook = xlrd.open_workbook(str(file_path))
            except Exception as error:
                logger.error(f"Не удалось открыть документ {file_path}: {error}")
                raise DocumentSearchError("Поврежденный или неподдерживаемый XLS файл.") from error
            
            for sheet in workbook.sheets():
                logger.debug(f"Сканирование листа: {sheet.name}")
                for row_idx in range(sheet.nrows):
                    for col_idx in range(sheet.ncols):
                        cell = sheet.cell(row_idx, col_idx)
                        if cell.value is None or cell.value == "":
                            continue
                        
                        text = self._normalize_cell_value(cell.value)
                        if text:
                            col_letter = self._xls_col_to_letter(col_idx)
                            cell_address = f"{sheet.name}!{col_letter}{row_idx + 1}"
                            
                            yield {
                                "text": text,
                                "display_text": self._format_cell_display(cell.value),
                                "sheet_name": sheet.name,
                                "row": row_idx + 1,
                                "column": col_letter,
                                "cell_address": cell_address,
                            }
        else:
            try:
                workbook = load_workbook(filename=file_path, read_only=True, data_only=True)
            except Exception as error:
                logger.error(f"Не удалось открыть документ {file_path}: {error}")
                raise DocumentSearchError("Поврежденный или неподдерживаемый XLSX файл.") from error

            for sheet in workbook.worksheets:
                logger.debug(f"Сканирование листа: {sheet.title}")
                for row_idx, row in enumerate(sheet.iter_rows(values_only=False), start=1):
                    for cell in row:
                        if cell.value is None:
                            continue
                        text = self._normalize_cell_value(cell.value)
                        if text:
                            yield {
                                "text": text,
                                "display_text": self._format_cell_display(cell.value),
                                "sheet_name": sheet.title,
                                "row": row_idx,
                                "column": cell.column_letter,
                                "cell_address": f"{sheet.title}!{cell.coordinate}",
                            }

            workbook.close()

    def extract_row_data(self, file_path: Path, sheet_name: str, row_number: int) -> Dict[str, Any]:
        """
        Извлекает данные из строки Excel, включая столбец "Количество" и другие столбцы.
        
        Поддерживает оба формата: .xlsx и .xls
        """
        suffix = file_path.suffix.lower()
        
        try:
            if suffix == ".xls":
                return self._extract_xls_row_data(file_path, sheet_name, row_number)
            else:
                return self._extract_xlsx_row_data(file_path, sheet_name, row_number)
        except Exception as error:
            logger.debug(f"Ошибка при извлечении данных строки {row_number} из {sheet_name}: {error}")
            return {}

    def _extract_xls_row_data(self, file_path: Path, sheet_name: str, row_number: int) -> Dict[str, Any]:
        """Извлечение данных из .xls файла."""
        if not XLRD_AVAILABLE:
            return {}
        
        workbook = xlrd.open_workbook(str(file_path))
        sheet = workbook.sheet_by_name(sheet_name)
        
        row_idx = row_number - 1
        if row_idx >= sheet.nrows:
            return {}
        
        row_values = []
        max_col = sheet.ncols
        for col_idx in range(max_col):
            cell = sheet.cell(row_idx, col_idx)
            row_values.append(self._format_cell_display(cell.value) if cell.value else "")
        
        column_headers = {}
        header_row = None
        
        for header_row_idx in range(min(5, sheet.nrows)):
            for col_idx in range(min(max_col, 20)):
                cell = sheet.cell(header_row_idx, col_idx)
                if cell.value:
                    header_value = str(cell.value).strip().lower()
                    if header_value == "количество" or (
                        header_value.startswith("количество") and "количество" not in column_headers
                    ):
                        col_letter = self._xls_col_to_letter(col_idx)
                        column_headers["количество"] = {"col": col_letter, "idx": col_idx}
                        if header_row is None:
                            header_row = header_row_idx
        
        if "количество" not in column_headers and max_col >= 4:
            column_headers["количество"] = {"col": "D", "idx": 3}
        
        cost_unit_col = None
        total_cost_col = None
        
        for header_row_idx in range(min(5, sheet.nrows)):
            for col_idx in range(min(max_col, 20)):
                cell = sheet.cell(header_row_idx, col_idx)
                if cell.value:
                    header_value = str(cell.value).strip().lower()
                    if ("стоимость единицы" in header_value or 
                        (header_value.startswith("стоимость") and "единицы" in header_value)):
                        if cost_unit_col is None:
                            col_letter = self._xls_col_to_letter(col_idx)
                            cost_unit_col = {"col": col_letter, "idx": col_idx, "name": str(cell.value).strip()}
                    if "общая стоимость" in header_value or header_value.startswith("общая стоимость"):
                        if total_cost_col is None:
                            col_letter = self._xls_col_to_letter(col_idx)
                            total_cost_col = {"col": col_letter, "idx": col_idx, "name": str(cell.value).strip()}
        
        result = {}
        if "количество" in column_headers:
            col_idx = column_headers["количество"]["idx"]
            if col_idx < len(row_values) and row_values[col_idx]:
                result["количество"] = {
                    "value": row_values[col_idx],
                    "column": column_headers["количество"]["col"],
                    "name": "Количество"
                }
        
        if cost_unit_col:
            col_idx = cost_unit_col["idx"]
            if col_idx < len(row_values) and row_values[col_idx]:
                result["стоимость_единицы"] = {
                    "value": row_values[col_idx],
                    "column": cost_unit_col["col"],
                    "name": cost_unit_col["name"]
                }
        
        if total_cost_col:
            col_idx = total_cost_col["idx"]
            if col_idx < len(row_values) and row_values[col_idx]:
                result["общая_стоимость"] = {
                    "value": row_values[col_idx],
                    "column": total_cost_col["col"],
                    "name": total_cost_col["name"]
                }
        
        return result

    def _extract_xlsx_row_data(self, file_path: Path, sheet_name: str, row_number: int) -> Dict[str, Any]:
        """Извлечение данных из .xlsx файла."""
        workbook = load_workbook(filename=file_path, read_only=True, data_only=True)
        sheet = workbook[sheet_name]
        
        row_values = []
        max_col = sheet.max_column
        for col_idx in range(1, max_col + 1):
            cell = sheet.cell(row=row_number, column=col_idx)
            row_values.append(self._format_cell_display(cell.value) if cell.value is not None else "")
        
        column_headers = {}
        header_row = None
        
        for header_row_idx in range(1, min(6, sheet.max_row + 1)):
            for col_idx in range(1, min(max_col + 1, 20)):
                cell = sheet.cell(row=header_row_idx, column=col_idx)
                if cell.value:
                    header_value = str(cell.value).strip().lower()
                    if header_value == "количество" or (
                        header_value.startswith("количество") and "количество" not in column_headers
                    ):
                        column_headers["количество"] = {"col": cell.column_letter, "idx": col_idx - 1}
                        if header_row is None:
                            header_row = header_row_idx
        
        if "количество" not in column_headers and max_col >= 4:
            column_headers["количество"] = {"col": "D", "idx": 3}
        
        cost_unit_col = None
        total_cost_col = None
        
        for header_row_idx in range(1, min(6, sheet.max_row + 1)):
            for col_idx in range(1, min(max_col + 1, 20)):
                cell = sheet.cell(row=header_row_idx, column=col_idx)
                if cell.value:
                    header_value = str(cell.value).strip().lower()
                    if ("стоимость единицы" in header_value or 
                        (header_value.startswith("стоимость") and "единицы" in header_value)):
                        if cost_unit_col is None:
                            cost_unit_col = {"col": cell.column_letter, "idx": col_idx - 1, "name": str(cell.value).strip()}
                    if "общая стоимость" in header_value or header_value.startswith("общая стоимость"):
                        if total_cost_col is None:
                            total_cost_col = {"col": cell.column_letter, "idx": col_idx - 1, "name": str(cell.value).strip()}
        
        workbook.close()
        
        result = {}
        if "количество" in column_headers:
            col_idx = column_headers["количество"]["idx"]
            if col_idx < len(row_values) and row_values[col_idx]:
                result["количество"] = {
                    "value": row_values[col_idx],
                    "column": column_headers["количество"]["col"],
                    "name": "Количество"
                }
        
        if cost_unit_col:
            col_idx = cost_unit_col["idx"]
            if col_idx < len(row_values) and row_values[col_idx]:
                result["стоимость_единицы"] = {
                    "value": row_values[col_idx],
                    "column": cost_unit_col["col"],
                    "name": cost_unit_col["name"]
                }
        elif max_col >= 5:
            for col_idx in [4, 5]:
                if col_idx < len(row_values) and row_values[col_idx]:
                    result["стоимость_единицы"] = {
                        "value": row_values[col_idx],
                        "column": get_column_letter(col_idx + 1),
                        "name": "Стоимость единицы"
                    }
                    break
        
        if total_cost_col:
            col_idx = total_cost_col["idx"]
            if col_idx < len(row_values) and row_values[col_idx]:
                result["общая_стоимость"] = {
                    "value": row_values[col_idx],
                    "column": total_cost_col["col"],
                    "name": total_cost_col["name"]
                }
        elif max_col >= 7:
            for col_idx in [6, 7, 8]:
                if col_idx < len(row_values) and row_values[col_idx]:
                    result["общая_стоимость"] = {
                        "value": row_values[col_idx],
                        "column": get_column_letter(col_idx + 1),
                        "name": "Общая стоимость"
                    }
                    break
        
        return result

    @staticmethod
    def _xls_col_to_letter(col_idx: int) -> str:
        """Конвертация номера столбца (0-based) в букву Excel (A, B, C, ...)."""
        result = ""
        col_idx += 1
        while col_idx > 0:
            col_idx -= 1
            result = chr(65 + (col_idx % 26)) + result
            col_idx //= 26
        return result

    @staticmethod
    def _normalize_cell_value(value: Any) -> Optional[str]:
        """Очистка значения ячейки перед поиском."""
        if isinstance(value, str):
            text = value.strip()
        elif isinstance(value, (int, float)):
            text = f"{value}".strip()
        else:
            text = str(value).strip()

        cleaned = re.sub(r"\s+", " ", text)
        return cleaned.casefold() if cleaned else None

    @staticmethod
    def _format_cell_display(value: Any) -> str:
        """Подготовка значения ячейки для отображения пользователю."""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
        return str(value).strip()

