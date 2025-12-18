"""
Виджет воронки продаж с канбан-доской
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from typing import Optional
from loguru import logger
from modules.styles.general_styles import apply_button_style, COLORS
from modules.crm.sales_funnel.kanban_board import SalesFunnelKanbanBoard
from modules.crm.sales_funnel.models import PipelineType, PipelineStage, Deal
from modules.crm.sales_funnel.pipeline_repository import PipelineRepository
from modules.crm.sales_funnel.deal_repository import DealRepository
from modules.crm.sales_funnel.deal_sync_service import DealSyncService


class SalesFunnelWidget(QWidget):
    """Виджет для отображения воронки продаж"""
    
    def __init__(
        self,
        pipeline_type: PipelineType,
        pipeline_repo: PipelineRepository,
        deal_repo: DealRepository,
        user_id: int = 1,
        tender_repo=None,
        parent=None
    ):
        super().__init__(parent)
        self.pipeline_type = pipeline_type
        self.pipeline_repo = pipeline_repo
        self.deal_repo = deal_repo
        self.user_id = user_id
        self.tender_repo = tender_repo
        self.kanban_board: Optional[SalesFunnelKanbanBoard] = None
        self.sync_service = None
        if tender_repo:
            self.sync_service = DealSyncService(deal_repo, tender_repo)
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Кнопка "Добавить сделку"
        btn_add = QPushButton("➕ Добавить сделку")
        apply_button_style(btn_add, 'primary')
        btn_add.clicked.connect(self.on_add_deal)
        layout.addWidget(btn_add)
    
    def load_data(self):
        """Загрузка данных воронки"""
        try:
            logger.info(f"Загрузка данных воронки: pipeline_type={self.pipeline_type.value}, user_id={self.user_id}")
            
            # Загружаем этапы
            stages = self.pipeline_repo.get_stages(self.pipeline_type)
            if not stages:
                logger.warning(f"Этапы для воронки {self.pipeline_type.value} не найдены")
                return
            
            # Загружаем сделки
            deals = self.deal_repo.get_deals(self.pipeline_type, self.user_id)
            logger.info(f"Загружено сделок: {len(deals)} для pipeline_type={self.pipeline_type.value}, user_id={self.user_id}")
            
            # Синхронизируем данные сделок с реестром закупок
            if self.sync_service:
                for deal in deals:
                    if deal.tender_id:
                        self.sync_service.sync_deal_with_tender(deal)
            
            # Создаем канбан-доску
            if self.kanban_board:
                self.layout().removeWidget(self.kanban_board)
                self.kanban_board.deleteLater()
            
            self.kanban_board = SalesFunnelKanbanBoard(
                self.pipeline_type,
                stages,
                deals,
                deal_repo=self.deal_repo,
                parent=self
            )
            self.layout().addWidget(self.kanban_board)
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных воронки: {e}")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось загрузить данные воронки:\n{str(e)}"
            )
    
    def on_add_deal(self):
        """Обработка добавления новой сделки"""
        # TODO: Открыть диалог создания сделки
        QMessageBox.information(self, "Информация", "Функция добавления сделки будет реализована")

