"""
Канбан-доска для управления закупками

Реализует функциональность drag-and-drop для перемещения карточек
между этапами закупок (как в Trello).
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QPainter, QPixmap
from typing import List, Dict, Any, Optional
from loguru import logger

# Импортируем единые стили
from modules.styles.general_styles import (
    apply_label_style, apply_frame_style, COLORS, FONT_SIZES, SIZES
)

# Импортируем карточку закупок
from modules.bids.bid_card import BidCard


class KanbanColumn(QFrame):
    """
    Колонка канбан-доски
    
    Содержит заголовок этапа и список карточек закупок.
    Поддерживает drag-and-drop для перемещения карточек.
    """
    
    def __init__(self, stage_name: str, parent=None):
        super().__init__(parent)
        self.stage_name = stage_name
        self.cards: List[BidCard] = []
        self.kanban_board = None  # Ссылка на родительскую доску
        self.setAcceptDrops(True)  # Включаем прием перетаскиваемых объектов
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса колонки"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Стиль колонки
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['white']};
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
                min-width: 280px;
                max-width: 320px;
            }}
        """)
        
        # Заголовок этапа
        header = QLabel(self.stage_name)
        apply_label_style(header, 'h3')
        header.setStyleSheet(f"""
            QLabel {{
                background: {COLORS['primary']};
                color: {COLORS['white']};
                padding: {SIZES['padding_normal']}px;
                border-radius: {SIZES['border_radius_small']}px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(header)
        
        # Счетчик карточек
        self.counter_label = QLabel("0")
        apply_label_style(self.counter_label, 'small')
        self.counter_label.setStyleSheet(f"color: {COLORS['text_light']};")
        layout.addWidget(self.counter_label)
        
        # Область прокрутки для карточек
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)
        
        # Контейнер для карточек
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.addStretch()  # Растягивающийся элемент внизу
        
        scroll_area.setWidget(self.cards_container)
        layout.addWidget(scroll_area)
    
    def add_card(self, card: BidCard):
        """Добавление карточки в колонку"""
        # Вставляем перед растягивающимся элементом
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        self.cards.append(card)
        self.update_counter()
        
        # Устанавливаем колонку как родителя для карточки
        card.set_parent_column(self)
    
    def remove_card(self, card: BidCard):
        """Удаление карточки из колонки"""
        if card in self.cards:
            self.cards.remove(card)
            self.cards_layout.removeWidget(card)
            card.setParent(None)
            self.update_counter()
    
    def update_counter(self):
        """Обновление счетчика карточек"""
        count = len(self.cards)
        self.counter_label.setText(str(count))
    
    def get_stage_name(self) -> str:
        """Получение названия этапа"""
        return self.stage_name
    
    def dragEnterEvent(self, event):
        """Обработка входа перетаскиваемого объекта в колонку"""
        if event.mimeData().hasText() and event.mimeData().text().startswith("BidCard:"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Обработка движения перетаскиваемого объекта в колонке"""
        if event.mimeData().hasText() and event.mimeData().text().startswith("BidCard:"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """Обработка сброса карточки в колонку"""
        if event.mimeData().hasText():
            text = event.mimeData().text()
            if text.startswith("BidCard:"):
                # Извлекаем ID карточки из текста
                try:
                    card_id = int(text.split(":")[1])
                except (ValueError, IndexError):
                    event.ignore()
                    return
                
                # Находим карточку на доске
                board = self.kanban_board
                if not board:
                    # Пытаемся найти через родителя
                    parent = self.parent()
                    while parent:
                        if isinstance(parent, KanbanBoard):
                            board = parent
                            break
                        parent = parent.parent()
                
                if board:
                    all_cards = board.get_all_cards()
                    for card in all_cards:
                        if id(card) == card_id:
                            # Получаем исходную колонку
                            old_column = card.get_parent_column()
                            if old_column and old_column != self:
                                # Перемещаем карточку
                                old_column.remove_card(card)
                                self.add_card(card)
                                logger.info(f"Карточка перемещена в этап '{self.stage_name}'")
                            elif not old_column:
                                # Карточка еще не была в колонке
                                self.add_card(card)
                            event.acceptProposedAction()
                            return
                
                event.ignore()
            else:
                event.ignore()
        else:
            event.ignore()


class KanbanBoard(QWidget):
    """
    Канбан-доска для управления закупками
    
    Содержит несколько колонок (этапов) и поддерживает
    drag-and-drop для перемещения карточек между колонками.
    """
    
    def __init__(self, stages: List[str], board_type: str = ""):
        """
        Инициализация канбан-доски
        
        Args:
            stages: Список названий этапов (колонок)
            board_type: Тип доски (например, "44ФЗ", "223ФЗ")
        """
        super().__init__()
        self.stages = stages
        self.board_type = board_type
        self.columns: List[KanbanColumn] = []
        self.dragged_card: Optional[BidCard] = None
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса канбан-доски"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Заголовок доски (если указан тип)
        if self.board_type:
            header = QLabel(f"Канбан-доска: {self.board_type}")
            apply_label_style(header, 'h2')
            header.setStyleSheet(f"margin-bottom: 15px; color: {COLORS['text_dark']};")
            main_layout.addWidget(header)
        
        # Горизонтальный layout для колонок
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(15)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        
        # Создаем колонки для каждого этапа
        for stage in self.stages:
            column = KanbanColumn(stage, self)
            self.columns.append(column)
            columns_layout.addWidget(column)
        
        columns_layout.addStretch()  # Растягивающийся элемент справа
        
        # Контейнер для колонок с прокруткой
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: {COLORS['secondary']};
            }}
        """)
        
        columns_widget = QWidget()
        columns_widget.setLayout(columns_layout)
        scroll_area.setWidget(columns_widget)
        
        main_layout.addWidget(scroll_area)
        
        # Сохраняем ссылку на доску для доступа из колонок
        for column in self.columns:
            column.kanban_board = self
    
    def add_card_to_stage(self, card: BidCard, stage_name: str):
        """
        Добавление карточки в указанный этап
        
        Args:
            card: Карточка закупок
            stage_name: Название этапа
        """
        for column in self.columns:
            if column.get_stage_name() == stage_name:
                column.add_card(card)
                return
        
        logger.warning(f"Этап '{stage_name}' не найден на доске")
    
    def move_card(self, card: BidCard, from_stage: str, to_stage: str):
        """
        Перемещение карточки между этапами
        
        Args:
            card: Карточка закупок
            from_stage: Исходный этап
            to_stage: Целевой этап
        """
        # Находим исходную колонку
        from_column = None
        for column in self.columns:
            if column.get_stage_name() == from_stage:
                from_column = column
                break
        
        # Находим целевую колонку
        to_column = None
        for column in self.columns:
            if column.get_stage_name() == to_stage:
                to_column = column
                break
        
        if from_column and to_column:
            from_column.remove_card(card)
            to_column.add_card(card)
            logger.info(f"Карточка перемещена из '{from_stage}' в '{to_stage}'")
        else:
            logger.error(f"Не удалось переместить карточку: этапы не найдены")
    
    def get_all_cards(self) -> List[BidCard]:
        """Получение всех карточек на доске"""
        all_cards = []
        for column in self.columns:
            all_cards.extend(column.cards)
        return all_cards

