"""
MODULE: modules.crm.sales_funnel.submenu_widget
RESPONSIBILITY: Submenu widget for Sales Funnel section.
ALLOWED: PyQt5, pathlib, loguru, modules.styles.*, modules.crm.folder_card, modules.crm.sales_funnel.models.
FORBIDDEN: Business logic.
ERRORS: None.

Виджет подменю для раздела Воронка продаж
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
from pathlib import Path
from typing import Dict
from loguru import logger

from modules.styles.general_styles import apply_label_style, apply_button_style, COLORS, SIZES
from modules.crm.folder_card import FolderCard
from modules.crm.sales_funnel.models import PipelineType


class SalesFunnelSubmenuWidget(QWidget):
    """Виджет подменю для воронок продаж"""
    
    submenu_item_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.item_cards: Dict[str, FolderCard] = {}
        self.init_ui()
        self.load_submenu_items()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Заголовок с кнопкой "Назад"
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)
        
        back_button = QPushButton("← Назад к разделам CRM")
        apply_button_style(back_button, 'outline')
        back_button.clicked.connect(self.on_back_clicked)
        header_layout.addWidget(back_button)
        
        header = QLabel("📊 Воронка продаж")
        apply_label_style(header, 'h1')
        header.setStyleSheet(f"color: {COLORS['primary']}; margin-bottom: {SIZES['padding_large']}px;")
        header_layout.addWidget(header)
        
        main_layout.addLayout(header_layout)
        
        # Grid layout для папок
        self.items_layout = QGridLayout()
        self.items_layout.setSpacing(20)
        self.items_layout.setContentsMargins(10, 10, 10, 10)
        
        main_layout.addLayout(self.items_layout)
    
    def load_submenu_items(self):
        """Загрузка элементов подменю"""
        submenu_items = [
            {
                'id': 'sales_funnel_participation',
                'name': 'Участвовать',
                'icon': '🎯',
            },
            {
                'id': 'sales_funnel_materials',
                'name': 'Поставка материалов',
                'icon': '📦',
            },
            {
                'id': 'sales_funnel_subcontracting',
                'name': 'Суб-подрядные работы',
                'icon': '🔧',
            },
        ]
        
        self.display_submenu_items(submenu_items)
    
    def update_counts(self, counts_by_pipeline: Dict[PipelineType, int]) -> None:
        """
        Обновление счетчиков для элементов подменю воронок продаж.
        
        counts_by_pipeline: словарь PipelineType -> количество сделок.
        """
        pipeline_map = {
            'sales_funnel_participation': PipelineType.PARTICIPATION,
            'sales_funnel_materials': PipelineType.MATERIALS_SUPPLY,
            'sales_funnel_subcontracting': PipelineType.SUBCONTRACTING,
        }
        
        for item_id, pipeline_type in pipeline_map.items():
            card = self.item_cards.get(item_id)
            if not card:
                continue
            count = counts_by_pipeline.get(pipeline_type, 0)
            card.update_count(count)
    
    def display_submenu_items(self, items_data: list):
        """Отображение элементов подменю"""
        row = 0
        col = 0
        max_cols = 4
        
        for item_data in items_data:
            folder_card = FolderCard(
                folder_id=item_data['id'],
                name=item_data['name'],
                icon=item_data['icon'],
                description=None,
                count=None,
                icon_path=None
            )
            folder_card.clicked.connect(self.on_submenu_item_clicked)
            self.item_cards[item_data['id']] = folder_card
            
            self.items_layout.addWidget(folder_card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def on_submenu_item_clicked(self, item_id: str):
        """Обработка клика на элемент подменю"""
        logger.info(f"Клик на элемент воронки продаж: {item_id}")
        self.submenu_item_clicked.emit(item_id)
    
    def on_back_clicked(self):
        """Обработка клика на кнопку 'Назад'"""
        self.submenu_item_clicked.emit('back_to_crm')

