"""
Колонка канбан-доски для воронок продаж
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget
from PyQt5.QtCore import Qt
from typing import List
from loguru import logger
from modules.styles.general_styles import apply_label_style, apply_text_color, apply_scroll_area_style, COLORS
from modules.styles.bids_styles import apply_kanban_header_style, apply_kanban_column_style
from modules.crm.sales_funnel.deal_card import DealCard
from modules.crm.sales_funnel.models import PipelineStage, Deal


class SalesFunnelKanbanColumn(QFrame):
    """Колонка канбан-доски для этапа воронки"""
    
    def __init__(self, stage: PipelineStage, parent=None):
        super().__init__(parent)
        self.stage = stage
        self.cards: List[DealCard] = []
        self.kanban_board = None
        self.setAcceptDrops(True)
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса колонки"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        apply_kanban_column_style(self)
        self.setMinimumWidth(280)
        self.setMaximumWidth(320)
        
        # Заголовок этапа
        header = QLabel(self.stage.name)
        apply_label_style(header, 'h3')
        apply_kanban_header_style(header)
        layout.addWidget(header)
        
        # Счетчик карточек
        self.counter_label = QLabel("0")
        apply_label_style(self.counter_label, 'small')
        apply_text_color(self.counter_label, 'text_light')
        # Убеждаемся, что счетчик виден
        self.counter_label.setVisible(True)
        layout.addWidget(self.counter_label)
        
        # Область прокрутки для карточек
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        apply_scroll_area_style(scroll_area, 'transparent')
        
        # Контейнер для карточек
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.addStretch()
        
        scroll_area.setWidget(self.cards_container)
        layout.addWidget(scroll_area)
    
    def add_card(self, card: DealCard):
        """Добавление карточки в колонку"""
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        self.cards.append(card)
        self.update_counter()
        card.set_parent_column(self)
    
    def remove_card(self, card: DealCard):
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
    
    def get_stage_id(self) -> int:
        """Получение ID этапа"""
        return self.stage.id if self.stage.id else 0
    
    def dragEnterEvent(self, event):
        """Обработка входа перетаскиваемого объекта в колонку"""
        if event.mimeData().hasText() and event.mimeData().text().startswith("DealCard:"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Обработка движения перетаскиваемого объекта в колонке"""
        if event.mimeData().hasText() and event.mimeData().text().startswith("DealCard:"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """Обработка сброса карточки в колонку"""
        if event.mimeData().hasText():
            text = event.mimeData().text()
            if text.startswith("DealCard:"):
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
                        from modules.crm.sales_funnel.kanban_board import SalesFunnelKanbanBoard
                        if isinstance(parent, SalesFunnelKanbanBoard):
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
                                # Обновляем этап сделки в БД
                                deal = card.deal
                                old_stage_id = deal.stage_id
                                new_stage_id = self.stage.id
                                
                                if old_stage_id != new_stage_id and deal.id:
                                    # Обновляем в БД через репозиторий
                                    deal_repo = getattr(self, 'deal_repo', None) or getattr(board, 'deal_repo', None)
                                    if deal_repo:
                                        success = deal_repo.update_deal_stage(deal.id, new_stage_id)
                                        if success:
                                            deal.stage_id = new_stage_id
                                            logger.info(f"Сделка {deal.id} перемещена из этапа {old_stage_id} в {new_stage_id}")
                                        else:
                                            logger.error(f"Не удалось обновить этап сделки {deal.id}")
                                            event.ignore()
                                            return
                                
                                # Перемещаем карточку
                                old_column.remove_card(card)
                                self.add_card(card)
                                logger.info(f"Карточка перемещена в этап '{self.stage.name}'")
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

