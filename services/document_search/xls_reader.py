"""
Чтение .xls файлов через xlrd.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Iterable, Callable, Optional

from loguru import logger

from core.exceptions import DocumentSearchError
from services.document_search.excel_utils import xls_col_to_letter, normalize_cell_value, format_cell_display

try:
    import xlrd
    XLRD_AVAILABLE = True
    XLRD_VERSION = getattr(xlrd, '__version__', '0.0.0')
except ImportError:
    XLRD_AVAILABLE = False
    XLRD_VERSION = None

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def iter_xls_cells(
    file_path: Path,
    allow_fallback: bool = True,
    iter_xlsx_cells_func: Optional[Callable] = None,
    iter_pandas_cells_func: Optional[Callable] = None,
) -> Iterable[Dict[str, Any]]:
    """Итерация по .xls файлам с возможностью fallback на openpyxl и pandas."""
    # Собираем информацию о всех неудачных попытках для структурированного отчета
    failed_attempts = []
    
    # Попытка 1: xlrd (если доступен) - напрямую, без pandas
    if XLRD_AVAILABLE:
        try:
            # Пробуем открыть с разными параметрами для старых файлов
            try:
                workbook = handle_file_lock(
                    file_path,
                    lambda: xlrd.open_workbook(str(file_path), formatting_info=False)
                )
            except Exception:
                # Если не получилось, пробуем с другими параметрами
                try:
                    workbook = handle_file_lock(
                        file_path,
                        lambda: xlrd.open_workbook(str(file_path), on_demand=True)
                    )
                except Exception:
                    workbook = xlrd.open_workbook(str(file_path))
            
            for sheet in workbook.sheets():
                logger.debug(f"Сканирование листа: {sheet.name}")
                for row_idx in range(sheet.nrows):
                    for col_idx in range(sheet.ncols):
                        cell = sheet.cell(row_idx, col_idx)
                        if cell.value is None or cell.value == "":
                            continue
                        
                        text = normalize_cell_value(cell.value)
                        if text:
                            col_letter = xls_col_to_letter(col_idx)
                            cell_address = f"{sheet.name}!{col_letter}{row_idx + 1}"
                            
                            yield {
                                "text": text,
                                "display_text": format_cell_display(cell.value),
                                "sheet_name": sheet.name,
                                "row": row_idx + 1,
                                "column": col_letter,
                                "cell_address": cell_address,
                            }
            return
        except Exception as xlrd_error:
            error_msg = str(xlrd_error).lower()
            if "xlsx file" in error_msg:
                # Файл имеет расширение .xls, но это XLSX
                if allow_fallback and iter_xlsx_cells_func:
                    yield from iter_xlsx_cells_func(file_path)
                    return
            
            # Добавляем информацию о неудачной попытке
            failed_attempts.append(("xlrd", str(xlrd_error)[:100]))
    
    # Попытка 2: openpyxl напрямую (если файл на самом деле .xlsx с неправильным расширением)
    if allow_fallback and iter_xlsx_cells_func:
        try:
            yield from iter_xlsx_cells_func(file_path)
            return
        except Exception as openpyxl_error:
            failed_attempts.append(("openpyxl", str(openpyxl_error)))
    
    # Попытка 3: пробуем через pandas с разными движками (без дублирования)
    if PANDAS_AVAILABLE and iter_pandas_cells_func:
        # Проверяем доступность движков
        available_engines = ['xlrd']
        if allow_fallback:
            available_engines.append('openpyxl')
        try:
            import python_calamine
            available_engines.append('calamine')
        except ImportError:
            pass
        
        for try_engine in available_engines:
            try:
                yield from iter_pandas_cells_func(file_path, engine=try_engine)
                return
            except Exception as pandas_error:
                failed_attempts.append((f"pandas ({try_engine})", str(pandas_error)))
                continue
    
    # Если все методы не сработали - выводим структурированный отчет
    from services.document_search.file_format_detector import detect_file_format
    detected_format = detect_file_format(file_path)
    
    # Формируем структурированный отчет о всех попытках
    attempts_summary = " | ".join([f"{method}: {error[:50]}" for method, error in failed_attempts[:5]])
    if len(failed_attempts) > 5:
        attempts_summary += f" ... и еще {len(failed_attempts) - 5} попыток"
    
    # Логируем как DEBUG - это ожидаемое поведение при поврежденных файлах
    logger.debug(
        f"Не удалось открыть файл {file_path.name} после всех попыток (попробовано {len(failed_attempts) + 1} методов, формат: {detected_format})"
    )
    
    error_msg = (
        f"Не удалось открыть файл {file_path.name} ни одним из доступных методов. "
        f"Определенный формат: {detected_format}. "
        f"Попробовано методов: {len(failed_attempts) + 1}. "
        f"Попробуйте установить xlrd==1.2.0 для поддержки старых .xls файлов."
    )
    raise DocumentSearchError(error_msg)

