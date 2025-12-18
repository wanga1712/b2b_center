"""
Нижняя панель (BottomBar) для ограничения приложения

Отображает статус приложения, индикаторы загрузки и служебную информацию.
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame
)
from PyQt5.QtCore import Qt
from loguru import logger

from modules.styles.general_styles import (
    apply_label_style, COLORS, SIZES
)


class BottomBar(QWidget):
    """
    Нижняя панель приложения
    
    Показывает статус, индикаторы загрузки и служебную информацию.
    """
    
    def __init__(self, parent=None):
        """
        Инициализация нижней панели
        
        Args:
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.setFixedHeight(30)  # Фиксированная высота панели
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QHBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 5, 20, 5)
        
        # Стиль панели
        self.setStyleSheet(f"""
            QWidget {{
                background: {COLORS['secondary']};
                border-top: 1px solid {COLORS['border']};
            }}
        """)
        
        # Статус приложения
        self.status_label = QLabel("✅ Готово")
        apply_label_style(self.status_label, 'small')
        self.status_label.setStyleSheet(f"color: {COLORS['text_dark']};")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Информация о версии или служебная информация
        self.info_label = QLabel("B2B AutoDesk v1.0")
        apply_label_style(self.info_label, 'small')
        self.info_label.setStyleSheet(f"color: {COLORS['text_light']};")
        layout.addWidget(self.info_label)
    
    def set_status(self, status: str, status_type: str = 'info'):
        """
        Установка статуса приложения
        
        Args:
            status: Текст статуса
            status_type: Тип статуса ('info', 'success', 'warning', 'error')
        """
        icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'loading': '⏳'
        }
        
        icon = icons.get(status_type, icons['info'])
        self.status_label.setText(f"{icon} {status}")
        
        colors = {
            'info': COLORS['text_dark'],
            'success': COLORS['success'],
            'warning': COLORS['warning'],
            'error': COLORS['error'],
            'loading': COLORS['primary']
        }
        
        self.status_label.setStyleSheet(f"color: {colors.get(status_type, colors['info'])};")
        logger.info(f"Статус обновлен: {status} ({status_type})")

