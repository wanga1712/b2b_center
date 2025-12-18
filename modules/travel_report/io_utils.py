"""Вспомогательные функции для работы с файлами отчетов по командировкам."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from shutil import copy2

from modules.travel_report.logic import TravelReportData


def get_trip_folder(base_dir: Path, trip_start: date, trip_end: date, city: str) -> Path:
    """
    Сформировать путь к папке командировки вида
    'дата начала - дата окончания, Город'.
    """
    safe_city = city.strip() or "Без_города"
    folder_name = (
        f"{trip_start.strftime('%d.%m.%Y')} - "
        f"{trip_end.strftime('%d.%m.%Y')}, {safe_city}"
    )
    return base_dir / folder_name


def copy_document_to_trip_folder(
    source_path: Path,
    base_dir: Path,
    trip_start: date,
    trip_end: date,
    city: str,
) -> Path:
    """
    Скопировать файл документа в папку командировки.

    Args:
        source_path: Исходный файл.
        base_dir: Базовая директория для командировок.
        trip_start: Дата начала командировки.
        trip_end: Дата окончания командировки.
        city: Город командировки.

    Returns:
        Путь к скопированному файлу.
    """
    trip_folder = get_trip_folder(base_dir, trip_start, trip_end, city)
    trip_folder.mkdir(parents=True, exist_ok=True)
    destination_path = trip_folder / source_path.name
    copy2(str(source_path), str(destination_path))
    return destination_path


def build_excel_filename(report: TravelReportData) -> str:
    """
    Сформировать имя файла Excel отчета по командировке.

    Args:
        report: Данные отчета.

    Returns:
        Имя файла с расширением .xlsx.
    """
    safe_city = report.city.replace("/", "-").replace("\\", "-")
    return (
        f"Отчет по командировке "
        f"{report.trip_start.strftime('%d.%m.%Y')} - "
        f"{report.trip_end.strftime('%d.%m.%Y')}, {safe_city}.xlsx"
    )


