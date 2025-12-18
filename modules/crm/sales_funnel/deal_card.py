"""
Карточка сделки для канбан-доски
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QMouseEvent
from typing import Optional
from loguru import logger
from modules.styles.general_styles import apply_label_style, COLORS, SIZES
from modules.crm.sales_funnel.models import Deal


class DealCard(QFrame):
    """Карточка сделки в канбан-доске"""
    
    clicked = pyqtSignal(Deal)
    
    def __init__(self, deal: Deal, parent=None):
        super().__init__(parent)
        self.deal = deal
        self._parent_column = None
        self.drag_start_position = QPoint()
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(False)
        self.init_ui()
        self.update_style()
    
    def init_ui(self):
        """Инициализация интерфейса карточки"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        self.setMinimumHeight(100)
        self.setMaximumHeight(200)
        
        # Название сделки
        name_label = QLabel(self.deal.name)
        name_label.setWordWrap(True)
        apply_label_style(name_label, 'normal')
        name_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text_dark']};")
        layout.addWidget(name_label)
        
        # Информация о закупке (если есть tender_id)
        if self.deal.tender_id:
            tender_info = QLabel(f"📋 Закупка №{self.deal.tender_id}")
            apply_label_style(tender_info, 'small')
            tender_info.setStyleSheet(f"color: {COLORS['text_light']};")
            layout.addWidget(tender_info)
        
        # Сумма (если есть)
        if self.deal.amount:
            amount_str = f"{self.deal.amount:,.0f}".replace(',', ' ')
            amount_label = QLabel(f"💰 {amount_str} ₽")
            apply_label_style(amount_label, 'small')
            amount_label.setStyleSheet(f"color: {COLORS['primary']};")
            layout.addWidget(amount_label)
        
        # Маржа (если есть)
        if self.deal.margin:
            margin_label = QLabel(f"📊 Маржа: {self.deal.margin:.1f}%")
            apply_label_style(margin_label, 'small')
            margin_label.setStyleSheet(f"color: {COLORS['text_light']};")
            layout.addWidget(margin_label)
        
        layout.addStretch()
    
    def update_style(self):
        """Обновление стиля карточки"""
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
            }}
            QFrame:hover {{
                border: 2px solid {COLORS['primary']};
                background: {COLORS['white']};
            }}
        """)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Обработка нажатия мыши на карточку"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Обработка двойного клика по карточке сделки"""
        if event.button() == Qt.LeftButton:
            # Открываем детальное окно сделки через сигнал
            self.clicked.emit(self.deal)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
    
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
        mime_data.setText(f"DealCard:{id(self)}")
        drag.setMimeData(mime_data)
        
        # Создаем визуальное представление карточки при перетаскивании
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        # Начинаем перетаскивание
        drop_action = drag.exec_(Qt.MoveAction)
        
        if drop_action == Qt.MoveAction:
            logger.info(f"Карточка сделки {self.deal.id} успешно перемещена")
    
    def set_parent_column(self, column):
        """Установка родительской колонки"""
        self._parent_column = column
    
    def get_parent_column(self):
        """Получение родительской колонки"""
        return self._parent_column
