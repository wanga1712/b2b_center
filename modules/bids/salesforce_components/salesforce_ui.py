from typing import Dict, Any, Callable
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from .salesforce_factories import (
    create_salesforce_header,
    create_salesforce_highlights,
    create_salesforce_actions
)
from .detail_section import SalesforceDetailSection


class SalesforceUI:
    """Координатор для создания Salesforce-стиля UI компонентов."""
    
    @staticmethod
    def create_header(tender_data: Dict[str, Any]) -> QWidget:
        """Создать заголовок в стиле Salesforce."""
        return create_salesforce_header(tender_data)
    
    @staticmethod
    def create_highlights(tender_data: Dict[str, Any]) -> QWidget:
        """Создать секцию с ключевыми метриками."""
        return create_salesforce_highlights(tender_data)
    
    @staticmethod
    def create_actions(
        on_download_all: Callable,
        on_mark_uninteresting: Callable,
        on_move_to_funnel: Callable
    ) -> QWidget:
        """Создать панель действий."""
        return create_salesforce_actions(
            on_download_all, on_mark_uninteresting, on_move_to_funnel
        )
    
    @staticmethod
    def create_detail_section(title: str, icon: str = "", parent=None) -> SalesforceDetailSection:
        """Создать секцию деталей."""
        return SalesforceDetailSection(title, icon, parent)
    
    @staticmethod
    def create_full_tender_ui(
        tender_data: Dict[str, Any],
        on_download_all: Callable,
        on_mark_uninteresting: Callable,
        on_move_to_funnel: Callable
    ) -> QWidget:
        """
        Создать полный UI для тендера в стиле Salesforce.
        
        Возвращает виджет с готовой компоновкой:
        - Заголовок
        - Ключевые метрики
        - Детальные секции (можно добавить позже)
        - Панель действий
        """
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Добавляем компоненты в правильном порядке
        layout.addWidget(SalesforceUI.create_header(tender_data))
        layout.addWidget(SalesforceUI.create_highlights(tender_data))
        
        # Здесь можно добавить детальные секции
        # Например: details_section = SalesforceUI.create_detail_section("Детали")
        # layout.addWidget(details_section)
        
        layout.addWidget(SalesforceUI.create_actions(
            on_download_all, on_mark_uninteresting, on_move_to_funnel
        ))
        
        return container