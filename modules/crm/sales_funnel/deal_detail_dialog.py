"""
Диалоговая форма детальной карточки сделки (воронка продаж).

Основной сценарий: клик по карточке сделки в воронке "Поставка материалов".
"""

from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QPushButton,
)
from PyQt5.QtCore import Qt

from modules.styles.general_styles import apply_label_style, apply_button_style
from modules.crm.sales_funnel.models import Deal
from modules.crm.sales_funnel.deal_detail_service import DealDetailService


class DealDetailDialog(QDialog):
    """Окно детальной карточки сделки."""

    def __init__(self, deal: Deal, detail_service: DealDetailService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.deal = deal
        self.detail_service = detail_service
        self.data: Dict[str, Any] = {}
        self.setWindowTitle(f"Карточка сделки — {deal.name}")
        self.resize(900, 700)
        self._init_ui()
        self._load_data()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        title = QLabel(f"Сделка: {self.deal.name}")
        apply_label_style(title, "h2")
        main_layout.addWidget(title)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Вкладки
        self.tab_overview = QWidget()
        self.tab_customer = QWidget()
        self.tab_contractor = QWidget()
        self.tab_items = QWidget()

        self.tabs.addTab(self.tab_overview, "Общая информация")
        self.tabs.addTab(self.tab_customer, "Заказчик")
        self.tabs.addTab(self.tab_contractor, "Подрядчик")
        self.tabs.addTab(self.tab_items, "КП / Товары")

        # Кнопка закрытия
        btn_close = QPushButton("Закрыть")
        apply_button_style(btn_close, "secondary")
        btn_close.clicked.connect(self.accept)
        main_layout.addWidget(btn_close, alignment=Qt.AlignRight)

        self._init_overview_tab()
        self._init_customer_tab()
        self._init_contractor_tab()
        self._init_items_tab()

    def _init_overview_tab(self) -> None:
        layout = QVBoxLayout(self.tab_overview)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.tender_info = QTextEdit()
        self.tender_info.setReadOnly(True)
        layout.addWidget(self._make_section_label("Закупка"))
        layout.addWidget(self.tender_info)

        self.deal_info = QTextEdit()
        self.deal_info.setReadOnly(True)
        layout.addWidget(self._make_section_label("Сделка"))
        layout.addWidget(self.deal_info)

    def _init_customer_tab(self) -> None:
        layout = QVBoxLayout(self.tab_customer)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.customer_info = QTextEdit()
        self.customer_info.setReadOnly(True)
        layout.addWidget(self._make_section_label("Заказчик"))
        layout.addWidget(self.customer_info)

        self.customer_contacts_table = self._create_contacts_table()
        layout.addWidget(self._make_section_label("Контакты заказчика"))
        layout.addWidget(self.customer_contacts_table)

    def _init_contractor_tab(self) -> None:
        layout = QVBoxLayout(self.tab_contractor)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.contractor_info = QTextEdit()
        self.contractor_info.setReadOnly(True)
        layout.addWidget(self._make_section_label("Подрядчик"))
        layout.addWidget(self.contractor_info)

        self.contractor_contacts_table = self._create_contacts_table()
        layout.addWidget(self._make_section_label("Контакты подрядчика"))
        layout.addWidget(self.contractor_contacts_table)

    def _init_items_tab(self) -> None:
        layout = QVBoxLayout(self.tab_items)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels(
            ["Наименование", "Код", "Ориг/Аналог", "Ед.", "Кол-во", "Итого"]
        )
        self.items_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.items_table)

    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        label = QLabel(text)
        apply_label_style(label, "h3")
        return label

    @staticmethod
    def _create_contacts_table() -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["ФИО", "Отдел", "Должность", "Телефон", "E-mail", "Роль"]
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table

    def _load_data(self) -> None:
        """Загружаем и раскладываем данные по вкладкам."""
        self.data = self.detail_service.build_deal_card(self.deal)

        self._fill_overview()
        self._fill_customer()
        self._fill_contractor()
        self._fill_items()

    def _fill_overview(self) -> None:
        tender = self.data.get("tender", {}) or {}
        deal_data = self.data.get("deal", {}) or {}

        tender_lines = []
        registry_type = tender.get("registry_type", "").upper()
        if registry_type:
            tender_lines.append(f"Реестр: {registry_type}")
        if tender.get("id"):
            tender_lines.append(f"ID реестра: {tender['id']}")
        if tender.get("tender_id"):
            tender_lines.append(f"ID площадки: {tender['tender_id']}")
        if tender.get("purchase_number"):
            tender_lines.append(f"Номер закупки: {tender['purchase_number']}")
        if tender.get("customer_full_name"):
            tender_lines.append(f"Заказчик: {tender['customer_full_name']}")
        if tender.get("contractor_full_name"):
            tender_lines.append(f"Подрядчик: {tender['contractor_full_name']}")
        if tender.get("region_name"):
            tender_lines.append(f"Регион: {tender['region_name']}")
        if tender.get("okpd_name"):
            tender_lines.append(f"ОКПД: {tender.get('okpd_main_code','')} {tender['okpd_name']}")
        if tender.get("final_price") or tender.get("initial_price"):
            price = tender.get("final_price") or tender.get("initial_price")
            tender_lines.append(f"Сумма закупки: {price}")
        if tender.get("platform_name"):
            tender_lines.append(f"Площадка: {tender['platform_name']}")

        self.tender_info.setPlainText("\n".join(tender_lines))

        deal_lines = [
            f"ID сделки: {deal_data.get('id')}",
            f"Тип воронки: {deal_data.get('pipeline_type')}",
            f"Этап ID: {deal_data.get('stage_id')}",
            f"Статус сделки: {deal_data.get('status')}",
            f"Статус закупки (ID): {deal_data.get('tender_status_id')}",
            f"Ответственный (user_id): {deal_data.get('user_id')}",
        ]
        amount = deal_data.get("amount")
        if amount is not None:
            deal_lines.append(f"Сумма сделки: {amount}")
        margin = deal_data.get("margin")
        if margin is not None:
            deal_lines.append(f"Маржа: {margin}%")

        self.deal_info.setPlainText("\n".join(filter(None, deal_lines)))

    def _fill_customer(self) -> None:
        customer = self.data.get("customer") or {}
        if customer:
            lines = [
                f"ID: {customer.get('id')}",
                f"Полное название: {customer.get('customer_full_name')}",
                f"Краткое название: {customer.get('customer_short_name')}",
                f"ИНН: {customer.get('customer_inn')}",
                f"КПП: {customer.get('customer_kpp')}",
                f"Юр. адрес: {customer.get('customer_legal_address')}",
                f"Факт. адрес: {customer.get('customer_actual_address')}",
                f"Телефон: {customer.get('contact_phone')}",
                f"E-mail: {customer.get('contact_email')}",
            ]
            self.customer_info.setPlainText("\n".join(filter(None, lines)))

        contacts = (self.data.get("contacts") or {}).get("customer") or []
        self._fill_contacts_table(self.customer_contacts_table, contacts)

    def _fill_contractor(self) -> None:
        contractor = self.data.get("contractor") or {}
        if contractor:
            lines = [
                f"ID: {contractor.get('id')}",
                f"Полное название: {contractor.get('full_name')}",
                f"Краткое название: {contractor.get('short_name')}",
                f"ИНН: {contractor.get('inn')}",
                f"КПП: {contractor.get('kpp')}",
                f"Юр. адрес: {contractor.get('legal_address')}",
                f"Телефон: {contractor.get('phone')}",
                f"E-mail: {contractor.get('email')}",
            ]
            self.contractor_info.setPlainText("\n".join(filter(None, lines)))

        contacts = (self.data.get("contacts") or {}).get("contractor") or []
        self._fill_contacts_table(self.contractor_contacts_table, contacts)

    @staticmethod
    def _fill_contacts_table(table: QTableWidget, contacts: list[dict[str, Any]]) -> None:
        table.setRowCount(len(contacts))
        for row_idx, contact in enumerate(contacts):
            table.setItem(row_idx, 0, QTableWidgetItem(str(contact.get("full_name", ""))))
            table.setItem(row_idx, 1, QTableWidgetItem(str(contact.get("department", ""))))
            table.setItem(row_idx, 2, QTableWidgetItem(str(contact.get("position", ""))))
            table.setItem(row_idx, 3, QTableWidgetItem(str(contact.get("phone_mobile", ""))))
            table.setItem(row_idx, 4, QTableWidgetItem(str(contact.get("email", ""))))
            role = contact.get("role") or ""
            if contact.get("is_primary"):
                role = f"{role} (основной)".strip()
            table.setItem(row_idx, 5, QTableWidgetItem(role))

    def _fill_items(self) -> None:
        items = self.data.get("items") or []
        self.items_table.setRowCount(len(items))

        for row_idx, item in enumerate(items):
            self.items_table.setItem(row_idx, 0, QTableWidgetItem(str(item.get("product_name", ""))))
            self.items_table.setItem(row_idx, 1, QTableWidgetItem(str(item.get("product_code", ""))))
            is_analog = "Аналог" if item.get("is_analog") else "Оригинал"
            self.items_table.setItem(row_idx, 2, QTableWidgetItem(is_analog))
            self.items_table.setItem(row_idx, 3, QTableWidgetItem(str(item.get("unit", ""))))
            self.items_table.setItem(row_idx, 4, QTableWidgetItem(str(item.get("quantity", ""))))
            self.items_table.setItem(row_idx, 5, QTableWidgetItem(str(item.get("total_price", ""))))


