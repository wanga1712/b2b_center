"""Контроллер поведения виджета отчета по командировке."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, Optional, List

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QPushButton,
    QLineEdit,
)

from config.settings import config
from modules.travel_report.constants import CATEGORIES
from modules.travel_report.io_utils import (
    copy_document_to_trip_folder,
    get_trip_folder,
    build_excel_filename,
)
from modules.travel_report.logic import (
    TravelExpenseItem,
    TravelReportData,
    TravelReportExcelExporter,
)


def format_balance_label(balance: float) -> str:
    """Форматирование остатка аванса."""
    rounded = round(balance, 2)
    if rounded > 0:
        return f"+{rounded:.2f}"
    if rounded < 0:
        return f"-{abs(rounded):.2f}"
    return "0.00"


def add_expense_row(
    table: QTableWidget,
    trip_start: QDate,
    row_docs: Dict[int, Optional[str]],
    handle_upload_cb,
) -> int:
    """Добавить строку расходов в таблицу и вернуть индекс строки."""
    row = table.rowCount()
    table.insertRow(row)

    category_combo = QComboBox()
    category_combo.addItems(CATEGORIES)
    table.setCellWidget(row, 0, category_combo)

    amount_edit = QDoubleSpinBox()
    amount_edit.setDecimals(2)
    amount_edit.setMaximum(1_000_000_000)
    amount_edit.setSingleStep(0.01)
    table.setCellWidget(row, 1, amount_edit)

    cheque_edit = QLineEdit()
    table.setCellWidget(row, 2, cheque_edit)

    document_date_edit = QDateEdit()
    document_date_edit.setCalendarPopup(True)
    document_date_edit.setDate(trip_start if trip_start.isValid() else QDate.currentDate())
    table.setCellWidget(row, 3, document_date_edit)

    balance_item = QTableWidgetItem("0.00")
    balance_item.setFlags(balance_item.flags() & ~balance_item.flags() | balance_item.flags())  # keep enabled/selectable
    table.setItem(row, 4, balance_item)

    upload_button = QPushButton("Загрузить чек/фото")
    upload_button.setFixedWidth(110)
    upload_button.clicked.connect(lambda _checked=False, r=row: handle_upload_cb(r))
    table.setCellWidget(row, 5, upload_button)

    row_docs[row] = None
    return row


def recalc_totals(table: QTableWidget, advance: QDoubleSpinBox, balance_label: QLabel) -> None:
    """Пересчитать расходы и остаток."""
    total = 0.0
    for row in range(table.rowCount()):
        amount_widget = table.cellWidget(row, 1)
        category_widget = table.cellWidget(row, 0)
        if isinstance(amount_widget, QDoubleSpinBox):
            category = category_widget.currentText() if isinstance(category_widget, QComboBox) else ""
            if category.lower() == "такси":
                continue
            total += float(amount_widget.value())

    balance = float(advance.value()) - total
    balance_text = format_balance_label(balance)
    balance_label.setText(balance_text)

    for row in range(table.rowCount()):
        item = table.item(row, 4)
        if item is None:
            item = QTableWidgetItem()
            table.setItem(row, 4, item)
        item.setText(balance_text)


def handle_upload(row: int, table: QTableWidget, row_docs: Dict[int, Optional[str]], trip_start: date, trip_end: date, city: str) -> Optional[str]:
    """Обработать сохранение файла в папку командировки."""
    base_dir_value = config.business_trip_docs_dir
    if not base_dir_value:
        raise ValueError("Путь BUSINESS_TRIP_DOCS_DIR не настроен в .env")

    from PyQt5.QtWidgets import QFileDialog

    source_path_str, _ = QFileDialog.getOpenFileName(
        table,
        "Выберите файл чека или фото",
        "",
        "Все файлы (*.*)",
    )
    if not source_path_str:
        return None

    source_path = Path(source_path_str)
    destination = copy_document_to_trip_folder(
        source_path,
        Path(base_dir_value),
        trip_start,
        trip_end,
        city,
    )
    row_docs[row] = str(destination)

    doc_item = table.item(row, 5)
    if doc_item is None:
        doc_item = QTableWidgetItem(source_path.name)
        table.setItem(row, 4, doc_item)
    else:
        doc_item.setText(source_path.name)

    return str(destination)


def collect_report_data(
    table: QTableWidget,
    trip_start: date,
    trip_end: date,
    city: str,
    advance: float,
    row_docs: Dict[int, Optional[str]],
) -> List[TravelExpenseItem]:
    """Собрать данные расходов из таблицы."""
    items: List[TravelExpenseItem] = []
    for row in range(table.rowCount()):
        category_widget = table.cellWidget(row, 0)
        amount_widget = table.cellWidget(row, 1)
        cheque_widget = table.cellWidget(row, 2)
        date_widget = table.cellWidget(row, 3)

        if not isinstance(category_widget, QComboBox) or not isinstance(
            amount_widget, QDoubleSpinBox
        ):
            continue

        category = category_widget.currentText()
        amount = float(amount_widget.value())
        if amount <= 0:
            continue

        document_date = None
        if isinstance(date_widget, QDateEdit):
            document_date = date_widget.date().toPyDate()

        items.append(
            TravelExpenseItem(
                category=category,
                amount=amount,
                document_date=document_date,
                document_path=row_docs.get(row),
                cheque_number=cheque_widget.text().strip() if isinstance(cheque_widget, QLineEdit) else None,
            )
        )
    return items


def build_report(
    trip_start: date,
    trip_end: date,
    city: str,
    advance: float,
    items: List[TravelExpenseItem],
) -> TravelReportData:
    """Создать объект отчета."""
    return TravelReportData(
        trip_start=trip_start,
        trip_end=trip_end,
        city=city,
        advance_amount=advance,
        items=items,
    )


def export_report(report: TravelReportData, base_dir: Path) -> Path:
    """Экспортировать отчет в Excel в папку командировки."""
    trip_folder = get_trip_folder(base_dir, report.trip_start, report.trip_end, report.city)
    exporter = TravelReportExcelExporter(trip_folder)
    filename = build_excel_filename(report)
    trip_folder.mkdir(parents=True, exist_ok=True)
    return exporter.export(report, filename)


