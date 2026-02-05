"""
MODULE: modules.bids.tender_card_ui
RESPONSIBILITY: UI component builders for tender cards.
ALLOWED: PyQt5, modules.styles.general_styles, modules.bids.tender_card_utils.
FORBIDDEN: Business logic.
ERRORS: None.

MODULE: modules.bids.tender_card_ui
RESPONSIBILITY: UI component builders for tender cards.
ALLOWED: PyQt5, modules.styles.general_styles, modules.bids.tender_card_utils.
FORBIDDEN: Business logic.
ERRORS: None.

Модуль для создания UI элементов карточки закупки.
"""

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt
from typing import Dict, Any, Optional

from modules.styles.general_styles import (
    apply_label_style, apply_text_style_light,
    apply_text_style_primary, apply_font_weight, apply_text_color, COLORS, SIZES, FONT_SIZES
)
from modules.bids.tender_card_utils import format_balance_holder, build_link_label


def create_header_layout(
    tender_data: Dict[str, Any], 
    select_checkbox,
    match_summary: Optional[Dict[str, Any]] = None
) -> QHBoxLayout:
    """Создание верхней строки с выбором, названием и бейджем приоритета."""
    header_layout = QHBoxLayout()
    header_layout.setSpacing(10)
    
    header_layout.addWidget(select_checkbox)
    
    # Название закупки
    purchase_name = tender_data.get('auction_name', 'Без названия')
    name_label = QLabel(purchase_name)
    apply_label_style(name_label, 'h2')
    name_label.setWordWrap(True)
    apply_font_weight(name_label)
    name_label.setContentsMargins(0, 0, 0, 5)
    header_layout.addWidget(name_label, 1)
    
    # Бейдж приоритета (Salesforce style)
    if match_summary:
        from modules.bids.tender_card_salesforce_styles import get_priority_color, get_priority_badge_style
        priority_color = get_priority_color(tender_data, match_summary)
        badge_info = get_priority_badge_style(priority_color)
        
        priority_badge = QLabel(badge_info['text'])
        priority_badge.setStyleSheet(
            f"""
            QLabel {{
                background: {badge_info['background']};
                color: {badge_info['color']};
                font-weight: bold;
                font-size: {FONT_SIZES['small']};
                padding: 4px 12px;
                border-radius: {SIZES['border_radius_small']}px;
            }}
            """
        )
        priority_badge.setFixedHeight(28)
        header_layout.addWidget(priority_badge)
    
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


def create_actions_layout(
    tender_data: Dict[str, Any],
    match_summary: Optional[Dict[str, Any]] = None,
    on_convert_clicked=None
) -> QHBoxLayout:
    """
    Создание строки с основными действиями (Salesforce style).
    
    Включает:
    - Бейджи с процентом совпадений
    - Кнопку конвертации в сделку
    """
    actions_layout = QHBoxLayout()
    actions_layout.setSpacing(10)
    
    # Показываем бейджи совпадений, если есть данные
    if match_summary:
        exact_count = match_summary.get('exact_count', 0)
        good_count = match_summary.get('good_count', 0)
        total_count = match_summary.get('total_count', 0)
        
        if exact_count > 0:
            exact_badge = QLabel(f"✓ 100%: {exact_count}")
            exact_badge.setStyleSheet(
                f"""
                QLabel {{
                    background: #d4edda;
                    color: #155724;
                    font-weight: bold;
                    font-size: {FONT_SIZES['normal']};
                    padding: 6px 12px;
                    border-radius: {SIZES['border_radius_small']}px;
                }}
                """
            )
            actions_layout.addWidget(exact_badge)
        
        if good_count > 0:
            good_badge = QLabel(f"⚡ 85%+: {good_count}")
            good_badge.setStyleSheet(
                f"""
                QLabel {{
                    background: #fff3cd;
                    color: #856404;
                    font-weight: bold;
                    font-size: {FONT_SIZES['normal']};
                    padding: 6px 12px;
                    border-radius: {SIZES['border_radius_small']}px;
                }}
                """
            )
            actions_layout.addWidget(good_badge)
        
        if total_count > 0:
            total_badge = QLabel(f"📊 Всего: {total_count}")
            total_badge.setStyleSheet(
                f"""
                QLabel {{
                    background: {COLORS['secondary']};
                    color: {COLORS['text_dark']};
                    font-weight: bold;
                    font-size: {FONT_SIZES['small']};
                    padding: 6px 12px;
                    border-radius: {SIZES['border_radius_small']}px;
                }}
                """
            )
            actions_layout.addWidget(total_badge)
    
    actions_layout.addStretch()
    
    # Кнопка конвертации в сделку (Salesforce style)
    convert_btn = QPushButton("🎯 Конвертировать в сделку")
    from modules.bids.tender_card_salesforce_styles import get_convert_button_style
    convert_btn.setStyleSheet(get_convert_button_style())
    convert_btn.setFixedHeight(32)
    if on_convert_clicked:
        convert_btn.clicked.connect(on_convert_clicked)
    actions_layout.addWidget(convert_btn)
    
    return actions_layout


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

