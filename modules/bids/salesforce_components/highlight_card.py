"""
MODULE: modules.bids.salesforce_components.highlight_card
RESPONSIBILITY: Карточка с ключевой метрикой в стиле Salesforce.
ALLOWED: PyQt5, modules.styles.general_styles
FORBIDDEN: Бизнес-логика или обработка данных.
ERRORS: None.

Карточка для отображения важных метрик с визуальным акцентом.
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from modules.styles.general_styles import COLORS, SIZES, FONT_SIZES


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