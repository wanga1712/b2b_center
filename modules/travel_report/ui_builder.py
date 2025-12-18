"""Построение UI для отчета по командировке."""

from __future__ import annotations

from dataclasses import dataclass
from PyQt5.QtCore import QDate
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QDateEdit,
    QDoubleSpinBox,
    QTableWidget,
    QPushButton,
    QWidget,
    QTextEdit,
    QSpacerItem,
    QSizePolicy,
)

from modules.styles.general_styles import apply_label_style, apply_button_style


@dataclass
class TravelReportControls:
    """Хранит ссылки на элементы управления отчета."""

    trip_start_edit: QDateEdit
    trip_end_edit: QDateEdit
    city_edit: QLineEdit
    advance_edit: QDoubleSpinBox
    expenses_table: QTableWidget
    balance_label: QLabel
    layout: QVBoxLayout
    company_inputs: list[QLineEdit]
    companies_container: QVBoxLayout
    add_company_button: QPushButton
    note_edit: QTextEdit
    ai_button: QPushButton
    copy_button: QPushButton


def _build_dates_city_row() -> tuple[QHBoxLayout, QDateEdit, QDateEdit, QLineEdit]:
    row = QHBoxLayout()
    row.setSpacing(8)

    start_edit = QDateEdit()
    start_edit.setCalendarPopup(True)
    start_edit.setDate(QDate.currentDate())

    end_edit = QDateEdit()
    end_edit.setCalendarPopup(True)
    end_edit.setDate(QDate.currentDate())

    city_edit = QLineEdit()

    row.addWidget(QLabel("Дата начала:"))
    row.addWidget(start_edit)
    row.addWidget(QLabel("Дата окончания:"))
    row.addWidget(end_edit)
    row.addWidget(QLabel("Город командировки:"))
    row.addWidget(city_edit, stretch=1)
    return row, start_edit, end_edit, city_edit


def _build_advance_row() -> tuple[QHBoxLayout, QDoubleSpinBox]:
    row = QHBoxLayout()
    row.setSpacing(8)

    advance_edit = QDoubleSpinBox()
    advance_edit.setDecimals(2)
    advance_edit.setMaximum(1_000_000_000)
    advance_edit.setSingleStep(0.01)

    row.addWidget(QLabel("Сумма аванса:"))
    row.addWidget(advance_edit)
    return row, advance_edit


def _build_table_header() -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(8)
    label = QLabel("Статьи расходов")
    apply_label_style(label, "h3")
    row.addWidget(label)

    add_button = QPushButton("+")
    add_button.setFixedWidth(32)
    apply_button_style(add_button, "primary")
    row.addWidget(add_button)
    row.addStretch(1)
    row.setProperty("add_button", add_button)
    return row


def _build_expenses_table() -> QTableWidget:
    table = QTableWidget(0, 6)
    table.setHorizontalHeaderLabels(
        [
            "Статья",
            "Фактические расходы",
            "Номер чека",
            "Дата по чеку",
            "Аванс - расходы",
            "Документ",
        ]
    )
    header = table.horizontalHeader()
    header.setStretchLastSection(True)
    header.setDefaultSectionSize(180)
    header.resizeSection(0, 260)
    header.resizeSection(1, 170)
    header.resizeSection(2, 140)
    header.resizeSection(3, 160)
    header.resizeSection(4, 150)
    header.resizeSection(5, 130)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(90)
    table.setMinimumHeight(260)
    table.setAlternatingRowColors(True)
    return table


def _build_balance_row() -> tuple[QHBoxLayout, QLabel]:
    row = QHBoxLayout()
    row.addStretch(1)
    row.addWidget(QLabel("Итоговый остаток аванса:"))
    balance_label = QLabel("0.00")
    apply_label_style(balance_label, "h3")
    row.addWidget(balance_label)
    return row, balance_label


def _build_actions_row() -> tuple[QHBoxLayout, QPushButton]:
    row = QHBoxLayout()
    row.addStretch(1)
    generate_button = QPushButton("Сформировать Excel-отчет")
    apply_button_style(generate_button, "primary")
    row.addWidget(generate_button)
    return row, generate_button


def _build_companies_row() -> tuple[QVBoxLayout, QVBoxLayout, list[QLineEdit], QPushButton]:
    layout = QVBoxLayout()
    header_row = QHBoxLayout()
    header_row.addWidget(QLabel("Компания(и), которые посещались:"))
    add_button = QPushButton("+")
    add_button.setFixedWidth(32)
    apply_button_style(add_button, "primary")
    header_row.addWidget(add_button)
    header_row.addStretch(1)
    layout.addLayout(header_row)

    fields_container = QVBoxLayout()
    layout.addLayout(fields_container)

    first_input = QLineEdit()
    fields_container.addWidget(first_input)
    return layout, fields_container, [first_input], add_button


def _build_note_row() -> tuple[QVBoxLayout, QTextEdit, QPushButton, QPushButton]:
    layout = QVBoxLayout()
    label = QLabel("Текст для отчета")
    apply_label_style(label, "h3")
    layout.addWidget(label)

    note_edit = QTextEdit()
    layout.addWidget(note_edit)

    buttons_row = QHBoxLayout()
    buttons_row.addStretch(1)
    
    copy_button = QPushButton("Скопировать текст")
    apply_button_style(copy_button, "outline")
    buttons_row.addWidget(copy_button)

    ai_button = QPushButton("Переписать с помощью ИИ")
    apply_button_style(ai_button, "secondary")
    buttons_row.addWidget(ai_button)

    layout.addLayout(buttons_row)

    return layout, note_edit, ai_button, copy_button


def build_travel_report_ui(parent: QWidget) -> TravelReportControls:
    """Создает макет и контролы отчета по командировке."""
    layout = QVBoxLayout(parent)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    header = QLabel("Отчет по командировке")
    apply_label_style(header, "h2")
    layout.addWidget(header)

    dates_row, start_edit, end_edit, city_edit = _build_dates_city_row()
    layout.addLayout(dates_row)

    advance_row, advance_edit = _build_advance_row()
    layout.addLayout(advance_row)

    header_row = _build_table_header()
    layout.addLayout(header_row)
    add_button = header_row.property("add_button")

    expenses_table = _build_expenses_table()
    layout.addWidget(expenses_table)

    balance_row, balance_label = _build_balance_row()
    layout.addLayout(balance_row)

    companies_row, companies_container, company_inputs, add_company_button = _build_companies_row()
    layout.addLayout(companies_row)

    note_row, note_edit, ai_button, copy_button = _build_note_row()
    layout.addLayout(note_row)

    actions_row, generate_button = _build_actions_row()
    layout.addLayout(actions_row)

    # Возвращаем ссылки на ключевые контролы
    controls = TravelReportControls(
        trip_start_edit=start_edit,
        trip_end_edit=end_edit,
        city_edit=city_edit,
        advance_edit=advance_edit,
        expenses_table=expenses_table,
        balance_label=balance_label,
        layout=layout,
        company_inputs=company_inputs,
        companies_container=companies_container,
        add_company_button=add_company_button,
        note_edit=note_edit,
        ai_button=ai_button,
        copy_button=copy_button,
    )
    # Доп. возврат кнопок через атрибуты для подключения сигналов
    controls.add_button = add_button  # type: ignore[attr-defined]
    controls.generate_button = generate_button  # type: ignore[attr-defined]
    return controls


