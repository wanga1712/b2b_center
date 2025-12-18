"""Модуль для инициализации UI диалога деталей закупки."""

from typing import Any, Dict, Optional, Callable
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
from modules.styles.general_styles import (
    apply_label_style, apply_button_style, apply_scroll_area_style
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
    """Инициализация интерфейса диалога"""
    layout = QVBoxLayout(dialog)
    layout.setSpacing(15)
    layout.setContentsMargins(20, 20, 20, 20)
    
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    apply_scroll_area_style(scroll, 'card')
    
    content_widget = QWidget()
    content_layout = QVBoxLayout(content_widget)
    content_layout.setSpacing(12)
    content_layout.setContentsMargins(15, 15, 15, 15)
    
    purchase_name = tender_data.get('auction_name', 'Без названия')
    name_label = QLabel(purchase_name)
    apply_label_style(name_label, 'h1')
    name_label.setWordWrap(True)
    content_layout.addWidget(name_label)
    content_layout.addWidget(create_separator())
    
    columns_layout = QHBoxLayout()
    columns_layout.setSpacing(15)
    
    left_widget = QWidget()
    left_layout = QVBoxLayout(left_widget)
    left_layout.setSpacing(12)
    
    left_layout.addWidget(create_info_section("Основная информация", [
        ("Номер контракта", tender_data.get('contract_number')),
        ("Площадка", tender_data.get('platform_name')),
        ("Балансодержатель", format_balance_holder(tender_data)),
        ("Регион", tender_data.get('region_name') or tender_data.get('delivery_region')),
    ]))
    
    left_layout.addWidget(create_info_section("Участники", [
        ("Заказчик", tender_data.get('customer_full_name') or tender_data.get('customer_short_name')),
        ("Подрядчик", tender_data.get('contractor_full_name') or tender_data.get('contractor_short_name')),
    ]))
    
    okpd_code = tender_data.get('okpd_sub_code') or tender_data.get('okpd_main_code', '')
    okpd_name = tender_data.get('okpd_name', '')
    if okpd_code:
        left_layout.addWidget(create_info_section("ОКПД", [
            ("Код", okpd_code),
            ("Название", okpd_name),
        ]))
    
    left_layout.addWidget(create_info_section("Финансы", [
        ("Начальная цена", format_price(tender_data.get('initial_price'))),
        ("Финальная цена", format_price(tender_data.get('final_price'))),
        ("Сумма обеспечения", format_price(tender_data.get('guarantee_amount'))),
    ]))
    
    left_layout.addWidget(create_info_section("Даты", [
        ("Дата начала", format_date(tender_data.get('start_date'))),
        ("Дата окончания", format_date(tender_data.get('end_date'))),
        ("Начало поставки", format_date(tender_data.get('delivery_start_date'))),
        ("Конец поставки", format_date(tender_data.get('delivery_end_date'))),
    ]))
    
    delivery_region = tender_data.get('delivery_region')
    delivery_address = tender_data.get('delivery_address')
    if delivery_region or delivery_address:
        left_layout.addWidget(create_info_section("Доставка", [
            ("Регион доставки", delivery_region),
            ("Адрес доставки", delivery_address),
        ]))
    
    document_links = tender_data.get('document_links', [])
    if document_links:
        left_layout.addWidget(create_documents_section(document_links, download_handler))
    
    tender_link = tender_data.get('tender_link')
    if tender_link:
        left_layout.addWidget(build_link_label("Ссылка на закупку", tender_link))
    
    left_layout.addStretch()
    columns_layout.addWidget(left_widget, 2)
    
    match_column = create_match_column(match_summary, match_details)
    if match_column:
        columns_layout.addWidget(match_column, 1)
    
    content_layout.addLayout(columns_layout)
    scroll.setWidget(content_widget)
    layout.addWidget(scroll)
    
    buttons_layout = QHBoxLayout()
    buttons_layout.addStretch()
    
    if move_to_funnel_handler is not None:
        btn_move_to_funnel = QPushButton("📊 Переместить в воронку продаж")
        apply_button_style(btn_move_to_funnel, "primary")
        btn_move_to_funnel.clicked.connect(move_to_funnel_handler)
        buttons_layout.addWidget(btn_move_to_funnel)
    
    if mark_uninteresting_handler is not None:
        btn_uninteresting = QPushButton("Пометить как неинтересную")
        apply_button_style(btn_uninteresting, "secondary")
        btn_uninteresting.clicked.connect(mark_uninteresting_handler)
        buttons_layout.addWidget(btn_uninteresting)
    
    btn_close = QPushButton("Закрыть")
    apply_button_style(btn_close, "secondary")
    btn_close.clicked.connect(dialog.accept)
    buttons_layout.addWidget(btn_close)
    
    layout.addLayout(buttons_layout)

