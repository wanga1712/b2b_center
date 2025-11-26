"""
Карточка закупки для канбан-доски

Представляет отдельную заявку/закупку с возможностью
перетаскивания между этапами.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame
)
from PyQt5.QtCore import Qt, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QPainter, QPixmap, QMouseEvent
from typing import Optional, Dict, Any
from loguru import logger

# Импортируем единые стили
from modules.styles.general_styles import (
    apply_label_style, COLORS, FONT_SIZES, SIZES
)


class BidCard(QFrame):
    """
    Карточка закупки
    
    Отображает информацию о закупке и поддерживает
    drag-and-drop для перемещения между колонками.
    """
    
    def __init__(self, bid_data: Dict[str, Any], parent=None):
        """
        Инициализация карточки
        
        Args:
            bid_data: Данные о закупке (номер, название, дата и т.д.)
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.bid_data = bid_data
        self.parent_column = None
        self.drag_start_position = QPoint()
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса карточки"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Стиль карточки
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['white']};
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
                min-height: 100px;
            }}
            QFrame:hover {{
                border: 2px solid {COLORS['primary']};
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
        """)
        
        # Включаем возможность перетаскивания
        self.setAcceptDrops(False)  # Карточка не принимает другие карточки
        
        # Номер закупки
        bid_number = self.bid_data.get('number', 'Без номера')
        number_label = QLabel(f"№ {bid_number}")
        apply_label_style(number_label, 'normal')
        number_label.setStyleSheet(f"""
            QLabel {{
                font-weight: bold;
                color: {COLORS['primary']};
            }}
        """)
        layout.addWidget(number_label)
        
        # Название закупки
        bid_name = self.bid_data.get('name', 'Без названия')
        name_label = QLabel(bid_name)
        apply_label_style(name_label, 'normal')
        name_label.setWordWrap(True)
        name_label.setStyleSheet(f"color: {COLORS['text_dark']};")
        layout.addWidget(name_label)
        
        # Дата (если указана)
        if 'date' in self.bid_data:
            date_label = QLabel(self.bid_data['date'])
            apply_label_style(date_label, 'small')
            date_label.setStyleSheet(f"color: {COLORS['text_light']};")
            layout.addWidget(date_label)
        
        # Сумма (если указана)
        if 'amount' in self.bid_data:
            amount_label = QLabel(f"Сумма: {self.bid_data['amount']}")
            apply_label_style(amount_label, 'small')
            amount_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['text_dark']};
                    font-weight: bold;
                }}
            """)
            layout.addWidget(amount_label)
        
        layout.addStretch()
    
    def set_parent_column(self, column):
        """Установка родительской колонки"""
        self.parent_column = column
    
    def get_parent_column(self):
        """Получение родительской колонки"""
        return self.parent_column
    
    def mousePressEvent(self, event: QMouseEvent):
        """Обработка нажатия мыши для начала перетаскивания"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Обработка движения мыши для drag-and-drop"""
        if not (event.buttons() & Qt.LeftButton):
            return
        
        # Проверяем, что перемещение достаточно большое
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return
        
        # Создаем объект перетаскивания
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Сохраняем данные о карточке
        mime_data.setText(f"BidCard:{id(self)}")
        drag.setMimeData(mime_data)
        
        # Создаем визуальное представление карточки при перетаскивании
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        # Начинаем перетаскивание
        drop_action = drag.exec_(Qt.MoveAction)
        
        if drop_action == Qt.MoveAction:
            logger.info("Карточка успешно перемещена")
    
    def get_bid_data(self) -> Dict[str, Any]:
        """Получение данных о закупке"""
        return self.bid_data

