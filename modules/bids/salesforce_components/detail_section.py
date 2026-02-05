"""
MODULE: modules.bids.salesforce_components.detail_section
RESPONSIBILITY: Секция информации в стиле Salesforce с полями.
ALLOWED: PyQt5, modules.styles.general_styles
FORBIDDEN: Бизнес-логика или обработка данных.
ERRORS: None.

Секция для отображения структурированной информации в стиле Salesforce.
"""

from typing import Any

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
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