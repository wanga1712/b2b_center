"""
MODULE: modules.bids.salesforce_settings_ui
RESPONSIBILITY: Factory for Salesforce-styled UI components.
ALLOWED: PyQt5, modules.styles.
FORBIDDEN: Business logic.
ERRORS: None.

UI компоненты для настроек закупок в стиле Salesforce.
Современный, чистый дизайн с группировкой и четкой визуальной иерархией.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QLineEdit,
    QPushButton, QComboBox, QListWidget
)
from PyQt5.QtCore import Qt
from modules.styles.general_styles import COLORS, SIZES, FONT_SIZES, apply_label_style


def create_salesforce_section_card(title: str, description: str = None) -> QFrame:
    """
    Создание карточки-секции в стиле Salesforce.
    
    Args:
        title: Заголовок секции
        description: Описание секции (опционально)
        
    Returns:
        QFrame с базовым layout для добавления контента
    """
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background: {COLORS['white']};
            border: 1px solid {COLORS['border']};
            border-radius: {SIZES['border_radius_normal']}px;
            padding: 0;
        }}
        """
    )
    
    layout = QVBoxLayout(card)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(15)
    
    # Заголовок секции
    title_label = QLabel(title)
    title_label.setStyleSheet(
        f"""
        font-size: {FONT_SIZES['h3']};
        font-weight: bold;
        color: {COLORS['text_dark']};
        border-bottom: 2px solid {COLORS['primary']};
        padding-bottom: 8px;
        """
    )
    layout.addWidget(title_label)
    
    # Описание (если есть)
    if description:
        desc_label = QLabel(description)
        desc_label.setStyleSheet(
            f"""
            font-size: {FONT_SIZES['small']};
            color: {COLORS['text_light']};
            font-style: italic;
            """
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
    
    return card


def create_salesforce_input_row(
    label_text: str,
    input_widget: QWidget,
    help_text: str = None
) -> QVBoxLayout:
    """
    Создание строки ввода в стиле Salesforce.
    
    Args:
        label_text: Текст лейбла
        input_widget: Виджет ввода (QLineEdit, QComboBox, и т.д.)
        help_text: Подсказка под полем (опционально)
        
    Returns:
        QVBoxLayout с лейблом, полем ввода и подсказкой
    """
    row_layout = QVBoxLayout()
    row_layout.setSpacing(6)
    
    # Лейбл
    label = QLabel(label_text)
    label.setStyleSheet(
        f"""
        font-size: {FONT_SIZES['normal']};
        color: {COLORS['text_dark']};
        font-weight: 600;
        """
    )
    row_layout.addWidget(label)
    
    # Поле ввода
    if isinstance(input_widget, (QLineEdit, QComboBox)):
        input_widget.setStyleSheet(
            f"""
            QLineEdit, QComboBox {{
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_small']}px;
                padding: 8px 12px;
                font-size: {FONT_SIZES['normal']};
                background: {COLORS['white']};
                min-height: {SIZES['input_height']}px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 2px solid {COLORS['primary']};
                background: #f0f7ff;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            """
        )
    
    row_layout.addWidget(input_widget)
    
    # Подсказка
    if help_text:
        help_label = QLabel(help_text)
        help_label.setStyleSheet(
            f"""
            font-size: {FONT_SIZES['small']};
            color: {COLORS['text_light']};
            font-style: italic;
            """
        )
        help_label.setWordWrap(True)
        row_layout.addWidget(help_label)
    
    return row_layout


def create_salesforce_button(text: str, button_type: str = 'primary') -> QPushButton:
    """
    Создание кнопки в стиле Salesforce.
    
    Args:
        text: Текст кнопки
        button_type: Тип кнопки ('primary', 'secondary', 'success', 'outline')
        
    Returns:
        QPushButton с Salesforce стилем
    """
    button = QPushButton(text)
    
    style_map = {
        'primary': {
            'bg': COLORS['primary'],
            'color': COLORS['white'],
            'hover_bg': COLORS['primary_dark'],
            'border': 'none',
        },
        'success': {
            'bg': COLORS['success'],
            'color': COLORS['white'],
            'hover_bg': '#7eb800',
            'border': 'none',
        },
        'secondary': {
            'bg': COLORS['secondary'],
            'color': COLORS['text_dark'],'hover_bg': '#e0e0e0',
            'border': f'1px solid {COLORS["border"]}',
        },
        'outline': {
            'bg': COLORS['white'],
            'color': COLORS['primary'],
            'hover_bg': COLORS['secondary'],
            'border': f'2px solid {COLORS["primary"]}',
        },
    }
    
    style = style_map.get(button_type, style_map['primary'])
    
    button.setStyleSheet(
        f"""
        QPushButton {{
            background: {style['bg']};
            color: {style['color']};
            border: {style['border']};
            border-radius: {SIZES['border_radius_small']}px;
            padding: 10px 24px;
            font-size: {FONT_SIZES['normal']};
            font-weight: bold;
            min-height: 40px;
        }}
        QPushButton:hover {{
            background: {style['hover_bg']};
        }}
        QPushButton:pressed {{
            background: {style['bg']};
            opacity: 0.8;
        }}
        """
    )
    button.setCursor(Qt.PointingHandCursor)
    
    return button


def create_salesforce_list_widget() -> QListWidget:
    """Создание списка в стиле Salesforce."""
    list_widget = QListWidget()
    list_widget.setStyleSheet(
        f"""
        QListWidget {{
            border: 1px solid {COLORS['border']};
            border-radius: {SIZES['border_radius_small']}px;
            background: {COLORS['white']};
            padding: 4px;
            font-size: {FONT_SIZES['normal']};
        }}
        QListWidget::item {{
            padding: 8px 12px;
            border-bottom: 1px solid {COLORS['secondary']};
            border-radius: {SIZES['border_radius_small']}px;
            margin: 2px 0;
        }}
        QListWidget::item:hover {{
            background: {COLORS['secondary']};
        }}
        QListWidget::item:selected {{
            background: {COLORS['primary']};
            color: {COLORS['white']};
            font-weight: bold;
        }}
        """
    )
    return list_widget

