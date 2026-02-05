"""
MODULE: modules.bids.tender_detail_dialog_init
RESPONSIBILITY: Initialize UI components for detail dialog.
ALLOWED: PyQt5, modules.styles.*, modules.bids.tender_detail_dialog_ui.
FORBIDDEN: Business logic.
ERRORS: None.

Модуль для инициализации UI диалога деталей закупки.
"""

from typing import Any, Dict, Optional, Callable
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
from modules.styles.general_styles import (
    apply_label_style, apply_button_style, apply_scroll_area_style, COLORS
)
from modules.bids.tender_detail_dialog_ui import (
    create_separator, create_info_section, create_documents_section, create_match_column
)
from modules.bids.tender_detail_dialog_format import format_price, format_date
from modules.bids.tender_card_utils import format_balance_holder, build_link_label


def init_dialog_ui(
    dialog,
    tender_data: Dict[str, Any],
    match_summary,
    match_details,
    download_handler,
    mark_uninteresting_handler: Optional[Callable[[], None]] = None,
    move_to_funnel_handler: Optional[Callable[[], None]] = None,
) -> None:
    """Инициализация интерфейса диалога в стиле Salesforce."""
    from modules.bids.tender_detail_salesforce_ui import (
        create_salesforce_header,
        create_salesforce_highlights,
        create_salesforce_actions,
        SalesforceDetailSection
    )
    
    layout = QVBoxLayout(dialog)
    layout.setSpacing(0)
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Заголовок (Salesforce style)
    header = create_salesforce_header(tender_data)
    layout.addWidget(header)
    
    # Скроллируемый контент
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    # Исправление: используем 'secondary' вместо несуществующего 'background'
    background_color = COLORS.get('background', COLORS.get('secondary', '#F5F5F5'))
    scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {background_color}; }}")
    
    content_widget = QWidget()
    content_layout = QVBoxLayout(content_widget)
    content_layout.setSpacing(20)
    content_layout.setContentsMargins(20, 20, 20, 20)
    
    # Ключевые метрики (Salesforce style)
    highlights = create_salesforce_highlights(tender_data)
    content_layout.addWidget(highlights)
    
    # Две колонки: основная информация + совпадения
    columns_layout = QHBoxLayout()
    columns_layout.setSpacing(20)
    
    # Левая колонка: секции с информацией
    left_widget = QWidget()
    left_layout = QVBoxLayout(left_widget)
    left_layout.setSpacing(15)
    
    # Секция "Основная информация"
    main_section = SalesforceDetailSection("Основная информация", "📋")
    main_section.add_field("Номер контракта", tender_data.get('contract_number'), highlight=True)
    main_section.add_field("Площадка", tender_data.get('platform_name'))
    main_section.add_field("Балансодержатель", format_balance_holder(tender_data))
    main_section.add_field("Регион", tender_data.get('region_name') or tender_data.get('delivery_region'))
    left_layout.addWidget(main_section)
    
    # Секция "Участники"
    participants_section = SalesforceDetailSection("Участники", "👥")
    participants_section.add_field(
        "Заказчик",
        tender_data.get('customer_full_name') or tender_data.get('customer_short_name')
    )
    participants_section.add_field(
        "Подрядчик",
        tender_data.get('contractor_full_name') or tender_data.get('contractor_short_name')
    )
    left_layout.addWidget(participants_section)
    
    # Секция "ОКПД"
    okpd_code = tender_data.get('okpd_sub_code') or tender_data.get('okpd_main_code', '')
    okpd_name = tender_data.get('okpd_name', '')
    if okpd_code:
        okpd_section = SalesforceDetailSection("ОКПД", "📦")
        okpd_section.add_field("Код", okpd_code)
        okpd_section.add_field("Название", okpd_name)
        left_layout.addWidget(okpd_section)
    
    # Секция "Финансы"
    finance_section = SalesforceDetailSection("Финансы", "💰")
    finance_section.add_field("Начальная цена", format_price(tender_data.get('initial_price')), highlight=True)
    finance_section.add_field("Финальная цена", format_price(tender_data.get('final_price')))
    finance_section.add_field("Сумма обеспечения", format_price(tender_data.get('guarantee_amount')))
    left_layout.addWidget(finance_section)
    
    # Секция "Даты"
    dates_section = SalesforceDetailSection("Даты", "📅")
    dates_section.add_field("Дата начала", format_date(tender_data.get('start_date')))
    dates_section.add_field("Дата окончания", format_date(tender_data.get('end_date')))
    dates_section.add_field("Начало поставки", format_date(tender_data.get('delivery_start_date')))
    dates_section.add_field("Конец поставки", format_date(tender_data.get('delivery_end_date')))
    left_layout.addWidget(dates_section)
    
    # Секция "Доставка"
    delivery_region = tender_data.get('delivery_region')
    delivery_address = tender_data.get('delivery_address')
    if delivery_region or delivery_address:
        delivery_section = SalesforceDetailSection("Доставка", "🚚")
        delivery_section.add_field("Регион доставки", delivery_region)
        delivery_section.add_field("Адрес доставки", delivery_address)
        left_layout.addWidget(delivery_section)
    
    # Секция "Документы"
    document_links = tender_data.get('document_links', [])
    if document_links:
        left_layout.addWidget(create_documents_section(document_links, download_handler))
    
    # Ссылка на закупку
    tender_link = tender_data.get('tender_link')
    if tender_link:
        left_layout.addWidget(build_link_label("Ссылка на закупку", tender_link))
    
    left_layout.addStretch()
    columns_layout.addWidget(left_widget, 2)
    
    # Правая колонка: совпадения
    match_column = create_match_column(match_summary, match_details)
    if match_column:
        columns_layout.addWidget(match_column, 1)
    
    content_layout.addLayout(columns_layout)
    scroll.setWidget(content_widget)
    layout.addWidget(scroll)
    
    # Панель действий внизу (Salesforce style)
    actions = create_salesforce_actions(
        lambda: download_handler(document_links) if document_links else None,
        mark_uninteresting_handler if mark_uninteresting_handler else lambda: None,
        move_to_funnel_handler if move_to_funnel_handler else lambda: None
    )
    layout.addWidget(actions)

