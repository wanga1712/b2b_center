"""
Модуль для создания UI элементов карточки закупки.
"""

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout
from typing import Dict, Any

from modules.styles.general_styles import (
    apply_label_style, apply_text_style_light,
    apply_text_style_primary, apply_font_weight, apply_text_color
)
from modules.bids.tender_card_utils import format_balance_holder, build_link_label


def create_header_layout(tender_data: Dict[str, Any], select_checkbox) -> QHBoxLayout:
    """Создание верхней строки с выбором и названием."""
    header_layout = QHBoxLayout()
    header_layout.setSpacing(10)
    
    header_layout.addWidget(select_checkbox)
    
    purchase_name = tender_data.get('auction_name', 'Без названия')
    name_label = QLabel(purchase_name)
    apply_label_style(name_label, 'h2')  # Используем стандартные стили (теперь увеличенные)
    name_label.setWordWrap(True)
    # Стиль h2 уже содержит color: text_dark, поэтому apply_text_color не нужен
    apply_font_weight(name_label)
    name_label.setContentsMargins(0, 0, 0, 5)
    header_layout.addWidget(name_label, 1)
    
    return header_layout


def create_info_layout(tender_data: Dict[str, Any]) -> QHBoxLayout:
    """Создание строки с основной информацией."""
    info_layout = QHBoxLayout()
    info_layout.setSpacing(15)
    
    contract_number = tender_data.get('contract_number', '')
    if contract_number:
        contract_label = QLabel(f"№ {contract_number}")
        apply_label_style(contract_label, 'normal')  # Используем увеличенные стили для карточек
        apply_text_style_light(contract_label)
        info_layout.addWidget(contract_label)
    
    region_name = tender_data.get('region_name') or tender_data.get('delivery_region', '')
    if region_name:
        region_label = QLabel(f"📍 {region_name}")
        apply_label_style(region_label, 'normal')  # Используем увеличенные стили для карточек
        apply_text_style_light(region_label)
        info_layout.addWidget(region_label)
    
    customer_name = (
        tender_data.get('customer_short_name') or 
        tender_data.get('customer_full_name', '')
    )
    if customer_name:
        customer_label = QLabel(f"👤 {customer_name[:50]}")
        apply_label_style(customer_label, 'normal')  # Используем увеличенные стили для карточек
        apply_text_style_light(customer_label)
        customer_label.setToolTip(customer_name)
        info_layout.addWidget(customer_label)
    
    info_layout.addStretch()
    return info_layout


def create_price_date_layout(tender_data: Dict[str, Any]) -> QHBoxLayout:
    """Создание строки с ценой и датой."""
    from datetime import datetime
    
    price_date_layout = QHBoxLayout()
    price_date_layout.setSpacing(15)
    
    initial_price = tender_data.get('initial_price')
    if initial_price:
        price_str = f"{float(initial_price):,.0f}".replace(',', ' ')
        price_label = QLabel(f"💰 {price_str} ₽")
        apply_label_style(price_label, 'large')  # Используем увеличенные стили для карточек
        apply_text_style_primary(price_label)
        apply_font_weight(price_label)
        price_date_layout.addWidget(price_label)
    
    end_date = tender_data.get('end_date')
    if end_date:
        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except:
                pass
        if hasattr(end_date, 'strftime'):
            date_str = end_date.strftime('%d.%m.%Y')
            date_label = QLabel(f"📅 До {date_str}")
            apply_label_style(date_label, 'normal')  # Используем увеличенные стили для карточек
            apply_text_style_light(date_label)
            price_date_layout.addWidget(date_label)
    
    price_date_layout.addStretch()
    return price_date_layout


def create_meta_layout(tender_data: Dict[str, Any]) -> QHBoxLayout:
    """Создание строки с мета-информацией."""
    meta_layout = QHBoxLayout()
    meta_layout.setSpacing(15)
    meta_items = 0
    
    platform_name = tender_data.get('platform_name')
    if platform_name:
        platform_label = QLabel(f"🏛 {platform_name}")
        apply_label_style(platform_label, 'normal')  # Используем увеличенные стили для карточек
        apply_text_style_light(platform_label)
        meta_layout.addWidget(platform_label)
        meta_items += 1
    
    balance_holder_text = format_balance_holder(tender_data)
    if balance_holder_text:
        balance_label = QLabel(f"🏢 Балансодержатель: {balance_holder_text}")
        apply_label_style(balance_label, 'normal')  # Используем увеличенные стили для карточек
        apply_text_style_light(balance_label)
        meta_layout.addWidget(balance_label)
        meta_items += 1
    
    contractor_name = (
        tender_data.get("contractor_short_name")
        or tender_data.get("contractor_full_name")
    )
    if contractor_name:
        contractor_label = QLabel(f"🤝 Подрядчик: {contractor_name[:80]}")
        apply_label_style(contractor_label, "normal")
        apply_text_style_light(contractor_label)
        contractor_label.setToolTip(contractor_name)
        meta_layout.addWidget(contractor_label)
        meta_items += 1
    
    tender_link = tender_data.get('tender_link')
    if tender_link:
        link_label = build_link_label("Ссылка на закупку", tender_link)
        meta_layout.addWidget(link_label)
        meta_items += 1
    
    if meta_items:
        meta_layout.addStretch()
        return meta_layout
    return None


def create_okpd_label(tender_data: Dict[str, Any]) -> QLabel:
    """Создание метки с ОКПД кодом."""
    okpd_code = (
        tender_data.get('okpd_sub_code') or 
        tender_data.get('okpd_main_code', '')
    )
    if okpd_code:
        okpd_label = QLabel(f"ОКПД: {okpd_code}")
        apply_label_style(okpd_label, 'normal')  # Используем увеличенные стили для карточек
        apply_text_style_light(okpd_label)
        return okpd_label
    return None

