"""
MODULE: modules.bids.tender_detail_salesforce_ui
RESPONSIBILITY: Salesforce-style UI components for detail dialog.
ALLOWED: PyQt5, modules.styles.general_styles.
FORBIDDEN: Business logic.
ERRORS: None.

UI модуль для детальной карточки закупки в стиле Salesforce.
Современный, читаемый дизайн с акцентом на ключевую информацию.
"""

from typing import Any, Dict, List, Optional
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from modules.styles.general_styles import COLORS, SIZES, FONT_SIZES


class SalesforceDetailSection(QFrame):
    """Секция информации в стиле Salesforce."""
    
    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self.icon = icon
        self.fields = []
        self.init_ui()
    
    def init_ui(self):
        """Инициализация UI секции."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Заголовок секции
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        if self.icon:
            icon_label = QLabel(self.icon)
            icon_font = QFont()
            icon_font.setPointSize(18)
            icon_label.setFont(icon_font)
            header_layout.addWidget(icon_label)
        
        title_label = QLabel(self.title)
        title_label.setStyleSheet(
            f"""
            font-size: {FONT_SIZES['h2']};
            font-weight: bold;
            color: {COLORS['text_dark']};
            """
        )
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background: {COLORS['border']}; max-height: 1px;")
        layout.addWidget(separator)
        
        # Grid для полей (2 колонки)
        self.grid = QGridLayout()
        self.grid.setSpacing(15)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(3, 1)
        layout.addLayout(self.grid)
        
        # Стиль секции
        self.setStyleSheet(
            f"""
            SalesforceDetailSection {{
                background: {COLORS['white']};
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
            }}
            """
        )
    
    def add_field(self, label: str, value: Any, highlight: bool = False):
        """
        Добавить поле в секцию.
        
        Args:
            label: Название поля
            value: Значение поля
            highlight: Выделить поле (для ключевой информации)
        """
        if not value:
            return
        
        row = len(self.fields)
        col = 0 if row % 2 == 0 else 2  # Чередуем колонки
        grid_row = row // 2
        
        # Лейбл
        label_widget = QLabel(label)
        label_widget.setStyleSheet(
            f"""
            font-size: {FONT_SIZES['small']};
            color: {COLORS['text_light']};
            font-weight: bold;
            text-transform: uppercase;
            """
        )
        self.grid.addWidget(label_widget, grid_row, col, Qt.AlignTop)
        
        # Значение
        value_widget = QLabel(str(value))
        value_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
        value_widget.setWordWrap(True)
        
        if highlight:
            value_widget.setStyleSheet(
                f"""
                font-size: {FONT_SIZES['large']};
                color: {COLORS['primary']};
                font-weight: bold;
                """
            )
        else:
            value_widget.setStyleSheet(
                f"""
                font-size: {FONT_SIZES['normal']};
                color: {COLORS['text_dark']};
                """
            )
        
        self.grid.addWidget(value_widget, grid_row, col + 1, Qt.AlignTop)
        
        self.fields.append((label, value))


class SalesforceHighlightCard(QFrame):
    """Карточка с ключевой метрикой (большая, заметная)."""
    
    def __init__(self, label: str, value: str, icon: str, color: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.init_ui(label, value, icon, color)
    
    def init_ui(self, label: str, value: str, icon: str, color: str):
        """Инициализация UI карточки."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Иконка и лейбл
        top_layout = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_font = QFont()
        icon_font.setPointSize(24)
        icon_label.setFont(icon_font)
        top_layout.addWidget(icon_label)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet(
            f"""
            font-size: {FONT_SIZES['normal']};
            color: {COLORS['text_light']};
            font-weight: bold;
            """
        )
        top_layout.addWidget(label_widget)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        # Значение (большое)
        value_widget = QLabel(value)
        value_widget.setStyleSheet(
            f"""
            font-size: {FONT_SIZES['h1']};
            color: {color};
            font-weight: bold;
            """
        )
        layout.addWidget(value_widget)
        
        # Стиль карточки
        self.setStyleSheet(
            f"""
            SalesforceHighlightCard {{
                background: {COLORS['white']};
                border: 1px solid {COLORS['border']};
                border-left: 4px solid {color};
                border-radius: {SIZES['border_radius_normal']}px;
            }}
            SalesforceHighlightCard:hover {{
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }}
            """
        )


class SalesforceActionButton(QPushButton):
    """Кнопка действия в стиле Salesforce."""
    
    def __init__(self, text: str, icon: str, button_type: str = "primary", parent=None):
        super().__init__(f"{icon} {text}", parent)
        self.button_type = button_type
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)
        self._apply_style()
    
    def _apply_style(self):
        """Применить стиль кнопки."""
        if self.button_type == "primary":
            bg_color = COLORS['primary']
            hover_color = "#005a9e"
            text_color = COLORS['white']
        elif self.button_type == "success":
            bg_color = "#28a745"
            hover_color = "#218838"
            text_color = COLORS['white']
        elif self.button_type == "danger":
            bg_color = "#dc3545"
            hover_color = "#c82333"
            text_color = COLORS['white']
        else:  # secondary/outline
            bg_color = COLORS['white']
            hover_color = COLORS['secondary']
            text_color = COLORS['text_dark']
        
        border = f"2px solid {COLORS['border']}" if self.button_type == "outline" else "none"
        
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: {bg_color};
                color: {text_color};
                border: {border};
                border-radius: {SIZES['border_radius_small']}px;
                padding: 10px 20px;
                font-size: {FONT_SIZES['normal']};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {hover_color};
            }}
            QPushButton:pressed {{
                background: {hover_color};
                transform: scale(0.98);
            }}
            """
        )


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
    on_download_all,
    on_mark_uninteresting,
    on_move_to_funnel
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

