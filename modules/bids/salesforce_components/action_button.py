"""
MODULE: modules.bids.salesforce_components.action_button
RESPONSIBILITY: Кнопка действия в стиле Salesforce.
ALLOWED: PyQt5, modules.styles.general_styles
FORBIDDEN: Бизнес-логика или обработка действий.
ERRORS: None.

Стилизованная кнопка для различных действий в интерфейсе.
"""

from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt

from modules.styles.general_styles import COLORS, SIZES, FONT_SIZES


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