from __future__ import annotations

from __future__ import annotations

"""Виджет отчета по командировке (компактный, с разнесенной логикой)."""

from pathlib import Path
from typing import Optional, Dict
import json
import time

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QWidget, QMessageBox, QLineEdit, QVBoxLayout, QScrollArea

from config.settings import config
from modules.travel_report.ai_client import rewrite_text
from modules.travel_report.controller import (
    add_expense_row,
    recalc_totals,
    handle_upload,
    collect_report_data,
    build_report,
    export_report,
)
from modules.travel_report.ui_builder import build_travel_report_ui, TravelReportControls

DEBUG_LOG_PATH = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"


def _append_debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    """Запись отладочной информации по модулю отчетов в общий debug.log."""
    # region agent log
    payload = {
        "sessionId": "debug-session",
        "runId": "travel-report-run",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": time.time(),
    }
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # endregion


class TravelReportWidget(QWidget):
    """Встроенный виджет отчета по командировкам для раздела задач."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        self.controls: TravelReportControls = build_travel_report_ui(container)
        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)
        self._row_documents: Dict[int, Optional[str]] = {}

        self.controls.add_button.clicked.connect(self._handle_add_row_clicked)  # type: ignore[attr-defined]
        self.controls.generate_button.clicked.connect(self._handle_generate_clicked)  # type: ignore[attr-defined]
        self.controls.add_company_button.clicked.connect(self._handle_add_company)  # type: ignore[attr-defined]
        self.controls.ai_button.clicked.connect(self._handle_ai_rewrite)  # type: ignore[attr-defined]
        self.controls.copy_button.clicked.connect(self._handle_copy_text)  # type: ignore[attr-defined]

        self._handle_add_row_clicked()
        self.controls.advance_edit.valueChanged.connect(self._handle_recalc)

    def _handle_add_row_clicked(self) -> None:
        """Добавить строку расходов."""
        add_expense_row(
            self.controls.expenses_table,
            self.controls.trip_start_edit.date(),
            self._row_documents,
            self._handle_upload,
        )
        self._handle_recalc()

    def _handle_add_company(self) -> None:
        """Добавить новое поле компании."""
        new_input = QLineEdit()
        self.controls.companies_container.addWidget(new_input)
        self.controls.company_inputs.append(new_input)

    def _handle_recalc(self) -> None:
        """Пересчитать итоговый остаток аванса."""
        recalc_totals(
            self.controls.expenses_table,
            self.controls.advance_edit,
            self.controls.balance_label,
        )

    def _handle_upload(self, row: int) -> None:
        """Загрузка чека/фото в строке расходов."""
        try:
            handle_upload(
                row,
                self.controls.expenses_table,
                self._row_documents,
                self.controls.trip_start_edit.date().toPyDate(),
                self.controls.trip_end_edit.date().toPyDate(),
                self.controls.city_edit.text().strip(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Ошибка конфигурации", str(error))
        except Exception as error:
            QMessageBox.critical(self, "Ошибка сохранения файла", str(error))
        self._handle_recalc()

    def _handle_generate_clicked(self) -> None:
        """Сформировать Excel-отчет."""
        base_dir_value = config.business_trip_docs_dir
        if not base_dir_value:
            QMessageBox.warning(
                self,
                "Ошибка конфигурации",
                "Путь для документов командировок не настроен.\n"
                "Укажите BUSINESS_TRIP_DOCS_DIR в .env.",
            )
            return

        trip_start = self.controls.trip_start_edit.date().toPyDate()
        trip_end = self.controls.trip_end_edit.date().toPyDate()

        _append_debug_log(
            "R1",
            "widget.py:_handle_generate_clicked:before_validate_dates",
            "Проверка дат перед формированием отчета",
            {
                "trip_start": trip_start.isoformat(),
                "trip_end": trip_end.isoformat(),
                "advance": float(self.controls.advance_edit.value()),
            },
        )

        if trip_end < trip_start:
            QMessageBox.warning(
                self,
                "Неверные даты",
                "Дата окончания командировки не может быть раньше даты начала.",
            )
            return

        city = self.controls.city_edit.text().strip()
        if not city:
            QMessageBox.warning(
                self,
                "Не указан город",
                "Пожалуйста, укажите город командировки.",
            )
            return

        items = collect_report_data(
            self.controls.expenses_table,
            trip_start,
            trip_end,
            city,
            float(self.controls.advance_edit.value()),
            self._row_documents,
        )
        if not items:
            QMessageBox.warning(
                self,
                "Нет расходов",
                "Добавьте хотя бы одну строку с ненулевой суммой расходов.",
            )
            return

        companies = [c.text().strip() for c in self.controls.company_inputs if c.text().strip()]

        _append_debug_log(
            "R2",
            "widget.py:_handle_generate_clicked:before_build_report",
            "Сбор данных для отчета",
            {
                "items_count": len(items),
                "companies": companies,
                "has_note": bool(self.controls.note_edit.toPlainText().strip()),
            },
        )

        report = build_report(
            trip_start,
            trip_end,
            city,
            float(self.controls.advance_edit.value()),
            items,
        )
        report.companies = companies
        note_text = self.controls.note_edit.toPlainText().strip()
        if note_text:
            report.rewritten_note = note_text
        else:
            balance = report.get_balance()
            if balance > 0:
                report.rewritten_note = (
                    f"Сумма неистраченных авансовых средств составляет: {balance:.2f}.\n"
                    "Готов вернуть в компанию денежные средства любым из удобных способов:\n"
                    "- удержание неисзрасходованных средств в счет заработной платы;\n"
                    "- перевод с зарплатного счета на счет компании по счету."
                )

        _append_debug_log(
            "R3",
            "widget.py:_handle_generate_clicked:before_export",
            "Вызов export_report",
            {
                "balance": report.get_balance(),
                "companies_count": len(report.companies),
                "has_rewritten_note": bool(report.rewritten_note),
            },
        )

        try:
            output_path = export_report(report, Path(base_dir_value))
        except Exception as error:
            _append_debug_log(
                "R4",
                "widget.py:_handle_generate_clicked:export_error",
                "Ошибка при export_report",
                {"error_type": type(error).__name__, "error_msg": str(error)},
            )
            QMessageBox.critical(
                self,
                "Ошибка создания отчета",
                f"Не удалось создать Excel-отчет:\n{error}",
            )
            return

        _append_debug_log(
            "R5",
            "widget.py:_handle_generate_clicked:success",
            "Отчет успешно сформирован",
            {"output_path": str(output_path)},
        )

        QMessageBox.information(
            self,
            "Отчет создан",
            f"Отчет успешно создан:\n{output_path}",
        )

    def _handle_ai_rewrite(self) -> None:
        """Переписать текст деловым стилем через OpenRouter."""
        text = self.controls.note_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Пустой текст", "Введите текст для переписывания.")
            return
        try:
            rewritten = rewrite_text(text)
        except ValueError as error:
            QMessageBox.warning(self, "Ошибка конфигурации", str(error))
            return
        except Exception as error:
            QMessageBox.critical(self, "Ошибка переписывания", str(error))
            return
        self.controls.note_edit.setPlainText(rewritten)

    def _handle_copy_text(self) -> None:
        """Скопировать текст из поля примечания в буфер."""
        text = self.controls.note_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Пустой текст", "Нет текста для копирования.")
            return
        clipboard = self.controls.note_edit.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Скопировано", "Текст скопирован в буфер обмена.")

