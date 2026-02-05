"""
MODULE: modules.crm.sales_funnel.deal_detail_logic.data_fillers
RESPONSIBILITY: Populate Deal Card UI tabs with data (Overview, Customer, Contractor).
ALLOWED: PyQt5, loguru, typing.
FORBIDDEN: Database queries (files should receive pre-fetched data).
ERRORS: None.

Модуль для заполнения данных во вкладках детальной карточки сделки.

Содержит методы для заполнения информации о закупке, заказчике, подрядчике.
"""

from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QTextEdit, QLabel
from loguru import logger


class DealDataFillers:
    """Класс для заполнения данных в виджеты детальной карточки сделки."""
    
    @staticmethod
    def fill_overview(tender_info: QTextEdit, tender_link_label: QLabel, data: Dict[str, Any]) -> None:
        """Заполнение вкладки 'Общая информация'."""
        tender = data.get("tender", {}) or {}
        
        tender_lines = []
        
        # Номер закупки
        if tender.get("purchase_number"):
            tender_lines.append(f"📄 Номер закупки: {tender['purchase_number']}")
        
        # Название закупки
        if tender.get("auction_name"):
            tender_lines.append(f"📝 Название закупки: {tender['auction_name']}")
        
        # Заказчик (балансодержатель) - текстовое поле customer из реестра контрактов
        customer_balance_holder = tender.get("customer")
        
        # Организатор торгов - данные из таблицы customer по customer_id
        customer_organizer = data.get("customer", {}) or {}
        organizer_name = customer_organizer.get("customer_full_name") or customer_organizer.get("customer_short_name")
        
        if customer_balance_holder:
            tender_lines.append(f"🏢 Заказчик (балансодержатель): {customer_balance_holder}")
        
        if organizer_name:
            # Показываем организатора торгов только если он отличается от балансодержателя
            if organizer_name != customer_balance_holder:
                tender_lines.append(f"📋 Организатор торгов: {organizer_name}")
            # Если балансодержатель не указан, показываем организатора как основного
            elif not customer_balance_holder:
                tender_lines.append(f"🏢 Организатор торгов: {organizer_name}")
        
        # Подрядчик
        if tender.get("contractor_full_name"):
            tender_lines.append(f"🏗 Подрядчик: {tender['contractor_full_name']}")
        
        # ОКПД
        if tender.get("okpd_name"):
            okpd_code = tender.get('okpd_main_code', '')
            if okpd_code:
                tender_lines.append(f"🧾 ОКПД: {okpd_code} {tender['okpd_name']}")
            else:
                tender_lines.append(f"🧾 ОКПД: {tender['okpd_name']}")
        
        # Сумма закупки
        if tender.get("final_price") or tender.get("initial_price"):
            price = tender.get("final_price") or tender.get("initial_price")
            tender_lines.append(f"💰 Сумма закупки: {price:,.0f} ₽".replace(",", " "))
        
        # Площадка
        if tender.get("platform_name"):
            tender_lines.append(f"🛒 Площадка: {tender['platform_name']}")
        
        # Даты
        if tender.get("start_date"):
            tender_lines.append(f"📅 Дата начала торгов: {tender['start_date']}")
        if tender.get("end_date"):
            tender_lines.append(f"📅 Дата окончания подачи заявок: {tender['end_date']}")
        if tender.get("delivery_start_date"):
            tender_lines.append(f"🚚 Начало поставки: {tender['delivery_start_date']}")
        if tender.get("delivery_end_date"):
            tender_lines.append(f"🚚 Окончание поставки: {tender['delivery_end_date']}")

        tender_info.setPlainText("\n".join(tender_lines))

        # Кликабельная ссылка на закупку
        tender_link = tender.get("tender_link")
        if tender_link:
            tender_link_label.setText(f'<a href="{tender_link}">🔗 Открыть закупку на площадке</a>')
            tender_link_label.show()
        else:
            tender_link_label.hide()
    
    @staticmethod
    def fill_customer(customer_info: QTextEdit, customer_contacts_table: QTableWidget, data: Dict[str, Any]) -> None:
        """Заполнение вкладки 'Заказчик'."""
        customer = data.get("customer") or {}
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
            customer_info.setPlainText("\n".join(filter(None, lines)))

        contacts = (data.get("contacts") or {}).get("customer") or []
        DealDataFillers._fill_contacts_table(customer_contacts_table, contacts)
    
    @staticmethod
    def fill_contractor(contractor_info: QTextEdit, contractor_contacts_table: QTableWidget, data: Dict[str, Any]) -> None:
        """Заполнение вкладки 'Подрядчик'."""
        contractor = data.get("contractor") or {}
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
            contractor_info.setPlainText("\n".join(filter(None, lines)))

        contacts = (data.get("contacts") or {}).get("contractor") or []
        DealDataFillers._fill_contacts_table(contractor_contacts_table, contacts)
    
    @staticmethod
    def _fill_contacts_table(table: QTableWidget, contacts: list[dict[str, Any]]) -> None:
        """Заполнение таблицы контактов."""
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

