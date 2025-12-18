"""
Модуль для загрузки тендеров в виджете закупок

Содержит методы для загрузки различных типов тендеров (44ФЗ, 223ФЗ, новые, разыгранные)
"""

from typing import Optional
from loguru import logger

from modules.bids.tender_loader import TenderLoader
from modules.bids.tender_list_widget import TenderListWidget


class BidsTenderLoader:
    """
    Класс для загрузки тендеров в виджете закупок
    
    Инкапсулирует логику загрузки различных типов тендеров
    """
    
    def __init__(self, tender_loader: TenderLoader):
        """
        Инициализация загрузчика тендеров
        
        Args:
            tender_loader: Экземпляр TenderLoader для загрузки тендеров
        """
        self.tender_loader = tender_loader
    
    def load_tenders_44fz(
        self,
        widget: TenderListWidget,
        user_id: int,
        category_filter_combo: Optional[object] = None,
        force: bool = False,
        parent_widget: Optional[object] = None
    ):
        """Загрузка новых закупок 44ФЗ"""
        self.tender_loader.load_new_tenders_44fz(
            widget=widget,
            user_id=user_id,
            category_filter_combo=category_filter_combo,
            force=force,
            parent_widget=parent_widget
        )
    
    def load_tenders_223fz(
        self,
        widget: TenderListWidget,
        user_id: int,
        category_filter_combo: Optional[object] = None,
        force: bool = False,
        parent_widget: Optional[object] = None
    ):
        """Загрузка новых закупок 223ФЗ"""
        self.tender_loader.load_new_tenders_223fz(
            widget=widget,
            user_id=user_id,
            category_filter_combo=category_filter_combo,
            force=force,
            parent_widget=parent_widget
        )
    
    def load_won_tenders_44fz(
        self,
        widget: TenderListWidget,
        user_id: int,
        category_filter_combo: Optional[object] = None,
        force: bool = False,
        parent_widget: Optional[object] = None
    ):
        """Загрузка разыгранных закупок 44ФЗ"""
        self.tender_loader.load_won_tenders_44fz(
            widget=widget,
            user_id=user_id,
            category_filter_combo=category_filter_combo,
            force=force,
            parent_widget=parent_widget
        )
    
    def load_won_tenders_223fz(
        self,
        widget: TenderListWidget,
        user_id: int,
        category_filter_combo: Optional[object] = None,
        force: bool = False,
        parent_widget: Optional[object] = None
    ):
        """Загрузка разыгранных закупок 223ФЗ"""
        self.tender_loader.load_won_tenders_223fz(
            widget=widget,
            user_id=user_id,
            category_filter_combo=category_filter_combo,
            force=force,
            parent_widget=parent_widget
        )
    
    def load_commission_tenders_44fz(
        self,
        widget: TenderListWidget,
        user_id: int,
        category_filter_combo: Optional[object] = None,
        force: bool = False,
        parent_widget: Optional[object] = None
    ):
        """Загрузка закупок 44ФЗ со статусом 'Работа комиссии'"""
        self.tender_loader.load_commission_tenders_44fz(
            widget=widget,
            user_id=user_id,
            category_filter_combo=category_filter_combo,
            force=force,
            parent_widget=parent_widget
        )

