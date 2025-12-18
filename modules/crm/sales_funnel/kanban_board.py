"""
Канбан-доска для воронок продаж
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea
from PyQt5.QtCore import Qt
from typing import List, Optional
from loguru import logger
from modules.styles.general_styles import apply_label_style, COLORS
from modules.crm.sales_funnel.kanban_column import SalesFunnelKanbanColumn
from modules.crm.sales_funnel.deal_card import DealCard
from modules.crm.sales_funnel.models import PipelineStage, Deal, PipelineType


class SalesFunnelKanbanBoard(QWidget):
    """Канбан-доска для воронки продаж"""
    
    def __init__(
        self,
        pipeline_type: PipelineType,
        stages: List[PipelineStage],
        deals: List[Deal],
        deal_repo=None,
        parent=None
    ):
        super().__init__(parent)
        self.pipeline_type = pipeline_type
        self.stages = stages
        self.deals = deals
        self.deal_repo = deal_repo
        self.columns: List[SalesFunnelKanbanColumn] = []
        self.all_cards: List[DealCard] = []
        self.init_ui()
        self.load_deals()
    
    def init_ui(self):
        """Инициализация интерфейса канбан-доски"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title_map = {
            PipelineType.PARTICIPATION: "Участие в торгах",
            PipelineType.MATERIALS_SUPPLY: "Поставка материалов",
            PipelineType.SUBCONTRACTING: "Субподрядные работы",
        }
        title = title_map.get(self.pipeline_type, "Воронка продаж")
        
        header = QLabel(title)
        apply_label_style(header, 'h1')
        header.setStyleSheet(f"color: {COLORS['primary']}; margin-bottom: 20px;")
        main_layout.addWidget(header)
        
        # Горизонтальная прокрутка для колонок
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        # Контейнер для колонок
        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setSpacing(15)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.addStretch()
        
        # Создаем колонки для каждого этапа
        for stage in self.stages:
            column = SalesFunnelKanbanColumn(stage, self)
            column.kanban_board = self
            if self.deal_repo:
                column.deal_repo = self.deal_repo
            self.columns.append(column)
            columns_layout.insertWidget(columns_layout.count() - 1, column)
        
        scroll_area.setWidget(columns_container)
        main_layout.addWidget(scroll_area)
    
    def load_deals(self):
        """Загрузка сделок в колонки"""
        # Группируем сделки по этапам
        deals_by_stage = {}
        for deal in self.deals:
            if deal.stage_id not in deals_by_stage:
                deals_by_stage[deal.stage_id] = []
            deals_by_stage[deal.stage_id].append(deal)
        
        # Добавляем карточки в соответствующие колонки
        for column in self.columns:
            stage_id = column.get_stage_id()
            if stage_id in deals_by_stage:
                for deal in deals_by_stage[stage_id]:
                    card = DealCard(deal, column)
                    card.clicked.connect(self.on_deal_clicked)
                    column.add_card(card)
                    self.all_cards.append(card)
        
        # Принудительно обновляем все счетчики после загрузки
        for column in self.columns:
            column.update_counter()
    
    def on_deal_clicked(self, deal: Deal):
        """Обработка клика на карточку сделки"""
        logger.info(f"Клик на сделку: {deal.name} (ID: {deal.id})")
        # Открываем диалог детальной карточки сделки
        try:
            from modules.crm.sales_funnel.deal_detail_service import DealDetailService
            from modules.crm.sales_funnel.deal_detail_dialog import DealDetailDialog

            if not self.deal_repo or not hasattr(self.deal_repo, "db_manager"):
                logger.warning("deal_repo или db_manager не инициализированы, диалог сделки не открыт")
                return

            service = DealDetailService(self.deal_repo.db_manager)
            dialog = DealDetailDialog(deal, service, parent=self)
            dialog.exec_()
        except Exception as exc:  # pragma: no cover - UI-защита
            logger.error(f"Ошибка при открытии карточки сделки: {exc}", exc_info=True)
    
    def get_all_cards(self) -> List[DealCard]:
        """Получение всех карточек"""
        return self.all_cards

