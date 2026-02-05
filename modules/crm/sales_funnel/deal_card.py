"""
MODULE: modules.crm.sales_funnel.deal_card
RESPONSIBILITY: UI card widget for a single deal in Kanban.
ALLOWED: PyQt5, loguru, datetime, modules.styles.general_styles, modules.crm.sales_funnel.models.
FORBIDDEN: DB access.
ERRORS: None.

Карточка сделки для канбан-доски
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QMouseEvent
from typing import Optional
from datetime import date, datetime
from loguru import logger
from modules.styles.general_styles import apply_label_style, COLORS, SIZES, FONT_SIZES
from modules.crm.sales_funnel.models import Deal


class DealCard(QFrame):
    """Карточка сделки в канбан-доске"""
    
    clicked = pyqtSignal(Deal)
    
    def __init__(self, deal: Deal, parent=None):
        super().__init__(parent)
        self.deal = deal
        self._parent_column = None
        self.drag_start_position = QPoint()
        self._is_dragging = False
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(False)
        self._widgets = {}  # Сохраняем ссылки на виджеты для обновления
        self.init_ui()
        self.update_style()
    
    def update_card_data(self):
        """Обновление содержимого карточки на основе текущих данных сделки"""
        # Очищаем старые виджеты информации о закупке (но сохраняем название и сумму)
        if hasattr(self, '_widgets'):
            for widget in self._widgets.get('tender_info_widgets', []):
                if widget.parent() == self:
                    self.layout().removeWidget(widget)
                    widget.deleteLater()
            self._widgets['tender_info_widgets'] = []
        
        # Пересоздаем информацию о закупке
        self._add_tender_info()
    
    def init_ui(self):
        """Инициализация интерфейса карточки"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.setMinimumHeight(90)
        self.setMaximumHeight(200)

        # --------- Верхняя строка: название сделки ---------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)

        self.name_label = QLabel(self.deal.name)
        self.name_label.setWordWrap(True)
        apply_label_style(self.name_label, 'normal')
        self.name_label.setStyleSheet(
            f"font-weight: bold; color: {COLORS['text_dark']};"
        )
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # --------- Денежный блок: сумма + маржа ---------
        money_layout = QHBoxLayout()
        money_layout.setSpacing(4)

        self.amount_label = None
        self.margin_label = None

        if self.deal.amount:
            amount_str = f"{self.deal.amount:,.0f}".replace(",", " ")
            self.amount_label = QLabel(f"💰 {amount_str} ₽")
            apply_label_style(self.amount_label, "small")
            self.amount_label.setStyleSheet(f"color: {COLORS['primary']};")
            money_layout.addWidget(self.amount_label)

        money_layout.addStretch()

        if self.deal.margin:
            self.margin_label = QLabel(f"📊 {self.deal.margin:.1f}%")
            apply_label_style(self.margin_label, "small")
            self.margin_label.setStyleSheet(f"color: {COLORS['text_light']};")
            money_layout.addWidget(self.margin_label)

        # Добавляем денежный блок только если есть что показать,
        # чтобы не съедать вертикальное пространство.
        if self.amount_label or self.margin_label:
            main_layout.addLayout(money_layout)

        # --------- Информация о закупке из metadata ---------
        self._add_tender_info()

        main_layout.addStretch()
    
    def _add_tender_info(self):
        """Добавление информации о закупке из metadata"""
        # #region agent log
        import json
        import time
        log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
        try:
            metadata = self.deal.metadata or {}
            original_data = metadata.get("original_data", {}) or {}
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "deal-card",
                    "hypothesisId": "CARD1",
                    "location": "deal_card.py:_add_tender_info",
                    "message": "Deal card data check",
                    "data": {
                        "deal_id": self.deal.id,
                        "deal_name": self.deal.name,
                        "has_metadata": bool(self.deal.metadata),
                        "has_original_data": "original_data" in (metadata or {}),
                        "original_data_keys": list(original_data.keys())[:20] if original_data else [],
                        "auction_name": original_data.get("auction_name"),
                        "region_name": original_data.get("region_name"),
                        "start_date": str(original_data.get("start_date")) if original_data.get("start_date") else None,
                        "end_date": str(original_data.get("end_date")) if original_data.get("end_date") else None,
                        "delivery_start_date": str(original_data.get("delivery_start_date")) if original_data.get("delivery_start_date") else None,
                        "delivery_end_date": str(original_data.get("delivery_end_date")) if original_data.get("delivery_end_date") else None,
                    },
                    "timestamp": int(time.time() * 1000)
                }, ensure_ascii=False) + "\n")
        except Exception as e:
            pass
        # #endregion
        
        if not hasattr(self, '_widgets'):
            self._widgets = {'tender_info_widgets': []}
        if 'tender_info_widgets' not in self._widgets:
            self._widgets['tender_info_widgets'] = []
        
        tender_info_lines = []
        
        # Извлекаем данные из metadata
        metadata = self.deal.metadata or {}
        original_data = metadata.get("original_data", {}) or {}
        
        # Наименование закупки (auction_name из реестра)
        auction_name = original_data.get("auction_name")
        if auction_name:
            tender_info_lines.append(f"📝 {auction_name[:60]}{'...' if len(auction_name) > 60 else ''}")
        
        # Регион поставки из region_id через таблицу region (region_name)
        region_name = original_data.get("region_name")
        if region_name:
            tender_info_lines.append(f"📍 {region_name}")
        
        # Даты торгов и поставки
        date_format = "%d.%m.%Y"
        
        def format_date(date_value, label_prefix):
            """Форматирование даты для отображения"""
            if not date_value:
                return None
            if isinstance(date_value, date):
                return f"{label_prefix} {date_value.strftime(date_format)}"
            elif isinstance(date_value, str):
                try:
                    # Попытка парсинга ISO формата
                    if 'T' in date_value:
                        date_obj = datetime.fromisoformat(date_value.replace('Z', '+00:00')).date()
                    else:
                        date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
                    return f"{label_prefix} {date_obj.strftime(date_format)}"
                except:
                    return f"{label_prefix} {date_value}"
            return None
        
        start_date_str = format_date(original_data.get("start_date"), "📅 Начало торгов:")
        if start_date_str:
            tender_info_lines.append(start_date_str)
        
        end_date_str = format_date(original_data.get("end_date"), "📅 Окончание торгов:")
        if end_date_str:
            tender_info_lines.append(end_date_str)
        
        delivery_start_str = format_date(original_data.get("delivery_start_date"), "🚚 Начало поставки:")
        if delivery_start_str:
            tender_info_lines.append(delivery_start_str)
        
        delivery_end_str = format_date(original_data.get("delivery_end_date"), "🚚 Окончание поставки:")
        if delivery_end_str:
            tender_info_lines.append(delivery_end_str)
        
        # Добавляем информацию о закупке (без лишних рамок, просто текст внутри карточки)
        layout = self.layout()
        
        # #region agent log
        import json
        import time
        log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "display",
                    "hypothesisId": "DISPLAY1",
                    "location": "deal_card.py:_add_tender_info:before_add_widgets",
                    "message": "Before adding widgets to card",
                    "data": {
                        "deal_id": self.deal.id,
                        "tender_info_lines_count": len(tender_info_lines),
                        "tender_info_lines": tender_info_lines[:5],
                        "layout_count": layout.count(),
                    },
                    "timestamp": int(time.time() * 1000)
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        for line in tender_info_lines:
            info_label = QLabel(line)
            # Применяем только размер шрифта, без рамок и фона
            info_label.setStyleSheet(
                f"color: {COLORS['text_light']}; "
                f"font-size: {FONT_SIZES['small']}; "
                "background: transparent; "
                "border: none; "
                "padding: 0px; "
                "margin: 0px; "
                f"font-family: Arial;"
            )
            info_label.setWordWrap(True)
            info_label.setVisible(True)  # Явно устанавливаем видимость
            # Вставляем перед последним элементом (stretch)
            layout.insertWidget(layout.count() - 1, info_label)
            self._widgets['tender_info_widgets'].append(info_label)
        
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "display",
                    "hypothesisId": "DISPLAY2",
                    "location": "deal_card.py:_add_tender_info:after_add_widgets",
                    "message": "After adding widgets to card",
                    "data": {
                        "deal_id": self.deal.id,
                        "widgets_added": len(self._widgets.get('tender_info_widgets', [])),
                        "layout_count_after": layout.count(),
                    },
                    "timestamp": int(time.time() * 1000)
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
    
    def update_style(self):
        """Обновление стиля карточки"""
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['white']};
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_large']}px;
                border-left: 4px solid {COLORS['primary']};
            }}
            QFrame:hover {{
                border-color: {COLORS['primary']};
                background: {COLORS['secondary']};
            }}
        """)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Обработка нажатия мыши на карточку"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self._is_dragging = False
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Обработка двойного клика по карточке сделки"""
        if event.button() == Qt.LeftButton:
            # Открываем детальное окно сделки через сигнал
            logger.info(f"Двойной клик по карточке сделки {self.deal.id}")
            self.clicked.emit(self.deal)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Обработка движения мыши для drag-and-drop"""
        if not (event.buttons() & Qt.LeftButton):
            return
        
        # Проверяем, что перемещение достаточно большое для начала drag
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return
        
        # Помечаем, что начался drag, чтобы не обрабатывать как клик
        self._is_dragging = True
        
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
