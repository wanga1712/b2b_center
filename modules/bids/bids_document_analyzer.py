"""
Модуль для анализа документов в виджете закупок

Содержит методы для запуска анализа документов выбранных или всех тендеров
"""

from typing import List, Dict, Any, Optional
from loguru import logger
from PyQt5.QtWidgets import QMessageBox

from modules.bids.document_processor import DocumentProcessor
from modules.bids.tender_list_widget import TenderListWidget


class BidsDocumentAnalyzer:
    """
    Класс для анализа документов в виджете закупок
    
    Инкапсулирует логику запуска анализа документов
    """
    
    def __init__(self, document_processor: DocumentProcessor):
        """
        Инициализация анализатора документов
        
        Args:
            document_processor: Экземпляр DocumentProcessor для обработки документов
        """
        self.document_processor = document_processor
    
    def handle_analyze_selected_tenders(
        self,
        tenders_44fz_widget: TenderListWidget,
        tenders_223fz_widget: TenderListWidget,
        won_tenders_44fz_widget: Optional[TenderListWidget],
        won_tenders_223fz_widget: Optional[TenderListWidget],
        commission_tenders_44fz_widget: Optional[TenderListWidget],
        current_tab_text: str,
        parent_widget: Any
    ):
        """
        Обработка нажатия кнопки 'Анализ документации'
        
        Args:
            tenders_44fz_widget: Виджет новых закупок 44ФЗ
            tenders_223fz_widget: Виджет новых закупок 223ФЗ
            won_tenders_44fz_widget: Виджет разыгранных закупок 44ФЗ
            won_tenders_223fz_widget: Виджет разыгранных закупок 223ФЗ
            commission_tenders_44fz_widget: Виджет закупок "Работа комиссии" 44ФЗ
            current_tab_text: Текст текущей вкладки
            parent_widget: Родительский виджет
        """
        selected_44fz, selected_223fz = self._get_selected_tenders_from_tab(
            tenders_44fz_widget, tenders_223fz_widget,
            won_tenders_44fz_widget, won_tenders_223fz_widget,
            commission_tenders_44fz_widget, current_tab_text, from_all_widgets=True
        )
        
        if not selected_44fz and not selected_223fz:
            QMessageBox.warning(parent_widget, "Предупреждение", "Выберите хотя бы одну закупку для анализа")
            return
        
        reply = QMessageBox.question(
            parent_widget,
            "Подтверждение",
            f"Запустить анализ документации для {len(selected_44fz) + len(selected_223fz)} выбранных закупок?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._run_document_processing_for_selected(selected_44fz, selected_223fz, parent_widget)
    
    def handle_analyze_all_tenders(
        self,
        tenders_44fz_widget: TenderListWidget,
        tenders_223fz_widget: TenderListWidget,
        won_tenders_44fz_widget: Optional[TenderListWidget],
        won_tenders_223fz_widget: Optional[TenderListWidget],
        commission_tenders_44fz_widget: Optional[TenderListWidget],
        current_tab_text: str,
        parent_widget: Any
    ):
        """
        Обработка нажатия кнопки 'Анализировать все'
        
        Args:
            tenders_44fz_widget: Виджет новых закупок 44ФЗ
            tenders_223fz_widget: Виджет новых закупок 223ФЗ
            won_tenders_44fz_widget: Виджет разыгранных закупок 44ФЗ
            won_tenders_223fz_widget: Виджет разыгранных закупок 223ФЗ
            commission_tenders_44fz_widget: Виджет закупок "Работа комиссии" 44ФЗ
            current_tab_text: Текст текущей вкладки
            parent_widget: Родительский виджет
        """
        priority_44fz, priority_223fz = self._get_selected_tenders_from_tab(
            tenders_44fz_widget, tenders_223fz_widget,
            won_tenders_44fz_widget, won_tenders_223fz_widget,
            commission_tenders_44fz_widget, current_tab_text, from_all_widgets=False
        )
        
        registry_type, tender_type = self._get_registry_and_tender_type(current_tab_text)
        priority_count = len(priority_44fz) + len(priority_223fz)
        
        reply = QMessageBox.question(
            parent_widget,
            "Подтверждение",
            f"Запустить анализ документации для всех закупок{' ' + current_tab_text if registry_type else ''}?\n\n"
            f"Приоритетных (выбранных): {priority_count}\n"
            f"Приоритетные закупки будут обработаны первыми.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._run_document_processing_for_all(
                priority_44fz, priority_223fz, registry_type=registry_type,
                tender_type=tender_type, parent_widget=parent_widget
            )
    
    def _get_selected_tenders_from_tab(
        self,
        tenders_44fz_widget: TenderListWidget,
        tenders_223fz_widget: TenderListWidget,
        won_tenders_44fz_widget: Optional[TenderListWidget],
        won_tenders_223fz_widget: Optional[TenderListWidget],
        commission_tenders_44fz_widget: Optional[TenderListWidget],
        current_tab_text: str,
        from_all_widgets: bool = False
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Получение выбранных закупок из текущей вкладки"""
        selected_44fz = []
        selected_223fz = []
        
        def get_tenders(widget):
            return widget.get_selected_tenders() if hasattr(widget, 'get_selected_tenders') and widget else []
        
        if from_all_widgets or current_tab_text not in [
            "Новые закупки 44ФЗ", "Новые закупки 223ФЗ",
            "Разыгранные закупки 44ФЗ", "Разыгранные закупки 223ФЗ",
            "Работа комиссии 44 ФЗ"
        ]:
            # Получаем из всех виджетов
            selected_44fz = get_tenders(tenders_44fz_widget)
            selected_223fz = get_tenders(tenders_223fz_widget)
            if won_tenders_44fz_widget:
                selected_44fz.extend(get_tenders(won_tenders_44fz_widget))
            if won_tenders_223fz_widget:
                selected_223fz.extend(get_tenders(won_tenders_223fz_widget))
            if commission_tenders_44fz_widget:
                selected_44fz.extend(get_tenders(commission_tenders_44fz_widget))
        else:
            # Получаем только из текущей вкладки
            if current_tab_text == "Новые закупки 44ФЗ":
                selected_44fz = get_tenders(tenders_44fz_widget)
            elif current_tab_text == "Новые закупки 223ФЗ":
                selected_223fz = get_tenders(tenders_223fz_widget)
            elif current_tab_text == "Разыгранные закупки 44ФЗ":
                selected_44fz = get_tenders(won_tenders_44fz_widget)
            elif current_tab_text == "Разыгранные закупки 223ФЗ":
                selected_223fz = get_tenders(won_tenders_223fz_widget)
            elif current_tab_text == "Работа комиссии 44 ФЗ":
                selected_44fz = get_tenders(commission_tenders_44fz_widget)
        
        return selected_44fz, selected_223fz
    
    def _get_registry_and_tender_type(self, current_tab_text: str) -> tuple[Optional[str], str]:
        """Получение типа реестра и типа торгов из текста вкладки"""
        if current_tab_text == "Новые закупки 44ФЗ":
            return '44fz', 'new'
        elif current_tab_text == "Новые закупки 223ФЗ":
            return '223fz', 'new'
        elif current_tab_text == "Разыгранные закупки 44ФЗ":
            return '44fz', 'won'
        elif current_tab_text == "Разыгранные закупки 223ФЗ":
            return '223fz', 'won'
        elif current_tab_text == "Работа комиссии 44 ФЗ":
            return '44fz', 'commission'
        return None, 'new'
    
    def _run_document_processing_for_selected(
        self,
        selected_44fz: List[Dict[str, Any]],
        selected_223fz: List[Dict[str, Any]],
        parent_widget: Any
    ):
        """Запуск обработки документов для выбранных закупок"""
        self.document_processor.process_selected_tenders(selected_44fz, selected_223fz, parent_widget)
    
    def _run_document_processing_for_all(
        self,
        priority_44fz: List[Dict[str, Any]],
        priority_223fz: List[Dict[str, Any]],
        registry_type: Optional[str] = None,
        tender_type: str = 'new',
        parent_widget: Any = None
    ):
        """
        Запуск обработки документов для всех закупок с учетом приоритетных
        
        Args:
            priority_44fz: Приоритетные закупки 44ФЗ
            priority_223fz: Приоритетные закупки 223ФЗ
            registry_type: Тип реестра для анализа ('44fz', '223fz' или None для обоих)
            tender_type: Тип торгов ('new' для новых, 'won' для разыгранных)
            parent_widget: Родительский виджет
        """
        self.document_processor.process_all_tenders(
            priority_44fz, priority_223fz,
            registry_type=registry_type,
            tender_type=tender_type,
            parent_widget=parent_widget
        )

