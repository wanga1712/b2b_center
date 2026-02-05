from typing import Dict, Any, Callable
from PyQt6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

from .highlight_card import SalesforceHighlightCard
from .action_button import SalesforceActionButton

# Константы стилей (перенесены из оригинального файла)
COLORS = {
    'white': '#ffffff',
    'border': '#dddbda',
    'text_dark': '#080707',
    'text_light': '#706e6b',
    'primary': '#0070d2'
}

FONT_SIZES = {
    'h1': '24px',
    'normal': '14px'
}

def create_salesforce_header(tender_data: Dict[str, Any]) -> QWidget:
    """
    Создание заголовка в стиле Salesforce.
    
    Показывает название закупки, номер контракта и статус.
    """
    header = QFrame()
    header.setStyleSheet(
        f"""
        QFrame {{
            background: {COLORS['white']};
            border-bottom: 2px solid {COLORS['border']};
            padding: 20px;
        }}
        """
    )
    
    layout = QVBoxLayout(header)
    layout.setSpacing(10)
    
    # Название закупки
    name = tender_data.get('auction_name', 'Без названия')
    name_label = QLabel(name)
    name_label.setStyleSheet(
        f"""
        font-size: {FONT_SIZES['h1']};
        color: {COLORS['text_dark']};
        font-weight: bold;
        """
    )
    name_label.setWordWrap(True)
    layout.addWidget(name_label)
    
    # Метаинформация (номер контракта, регион)
    meta_layout = QHBoxLayout()
    
    contract_number = tender_data.get('contract_number', '')
    if contract_number:
        contract_label = QLabel(f"№ {contract_number}")
        contract_label.setStyleSheet(
            f"font-size: {FONT_SIZES['normal']}; color: {COLORS['text_light']};"
        )
        meta_layout.addWidget(contract_label)
    
    region = tender_data.get('region_name') or tender_data.get('delivery_region', '')
    if region:
        region_label = QLabel(f"📍 {region}")
        region_label.setStyleSheet(
            f"font-size: {FONT_SIZES['normal']}; color: {COLORS['text_light']};"
        )
        meta_layout.addWidget(region_label)
    
    meta_layout.addStretch()
    layout.addLayout(meta_layout)
    
    return header


def create_salesforce_highlights(tender_data: Dict[str, Any]) -> QWidget:
    """
    Создание секции с ключевыми метриками (как в Salesforce).
    
    Показывает сумму, дату окончания, заказчика в больших карточках.
    """
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setSpacing(15)
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Сумма закупки
    initial_price = tender_data.get('initial_price')
    if initial_price:
        price_str = f"{float(initial_price):,.0f} ₽".replace(',', ' ')
        price_card = SalesforceHighlightCard(
            "Начальная цена",
            price_str,
            "💰",
            COLORS['primary']
        )
        layout.addWidget(price_card)
    
    # Дата окончания
    end_date = tender_data.get('end_date')
    if end_date:
        from datetime import datetime
        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except:
                pass
        if hasattr(end_date, 'strftime'):
            date_str = end_date.strftime('%d.%m.%Y')
            date_card = SalesforceHighlightCard(
                "Дата окончания",
                date_str,
                "📅",
                "#ffc107"
            )
            layout.addWidget(date_card)
    
    # Заказчик (если короткое название)
    customer = tender_data.get('customer_short_name') or tender_data.get('customer_full_name', '')
    if customer and len(customer) < 40:
        customer_card = SalesforceHighlightCard(
            "Заказчик",
            customer,
            "👤",
            "#28a745"
        )
        layout.addWidget(customer_card)
    
    layout.addStretch()
    
    return container


def create_salesforce_actions(
    on_download_all: Callable,
    on_mark_uninteresting: Callable,
    on_move_to_funnel: Callable
) -> QWidget:
    """Создание панели действий (как в Salesforce)."""
    container = QFrame()
    container.setStyleSheet(
        f"""
        QFrame {{
            background: {COLORS['white']};
            border-top: 2px solid {COLORS['border']};
            padding: 15px 20px;
        }}
        """
    )
    
    layout = QHBoxLayout(container)
    layout.setSpacing(10)
    
    # Кнопка "Переместить в воронку" (главная)
    btn_funnel = SalesforceActionButton("Переместить в воронку", "🎯", "success")
    btn_funnel.clicked.connect(on_move_to_funnel)
    layout.addWidget(btn_funnel)
    
    # Кнопка "Скачать документы"
    btn_download = SalesforceActionButton("Скачать все документы", "⬇️", "primary")
    btn_download.clicked.connect(on_download_all)
    layout.addWidget(btn_download)
    
    layout.addStretch()
    
    # Кнопка "Не интересно"
    btn_uninteresting = SalesforceActionButton("Не интересно", "❌", "outline")
    btn_uninteresting.clicked.connect(on_mark_uninteresting)
    layout.addWidget(btn_uninteresting)
    
    return container