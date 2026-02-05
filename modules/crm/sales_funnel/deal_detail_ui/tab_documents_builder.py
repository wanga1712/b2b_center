"""
MODULE: modules.crm.sales_funnel.deal_detail_ui.tab_documents_builder
RESPONSIBILITY: UI Builder for the "Documents" tab in Deal Detail dialog.
ALLOWED: PyQt5, modules.styles.general_styles.
FORBIDDEN: Business logic, Direct DB access.
ERRORS: None.

UI билдер для вкладки "Документы закупки" детальной карточки сделки.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, QPushButton)
from PyQt5.QtCore import Qt

from modules.styles.general_styles import apply_button_style, apply_label_style, COLORS


class DocumentsTabBuilder:
    """Класс для построения вкладки 'Документы закупки'."""
    
    @staticmethod
    def build_documents_tab(tab_widget: QWidget) -> dict:
        """
        Построение вкладки 'Документы закупки'.
        
        Returns:
            dict с виджетами для последующего использования
        """
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Раздел: Найденные фразы
        phrases_label = DocumentsTabBuilder._make_section_label("📋 Найденные фразы в документации")
        layout.addWidget(phrases_label)
        
        # Скролл-область для фраз
        phrases_scroll = QScrollArea()
        phrases_scroll.setWidgetResizable(True)
        phrases_scroll.setStyleSheet(f"background-color: {COLORS['white']}; border: 1px solid {COLORS['border']};")
        
        phrases_container = QWidget()
        phrases_layout = QVBoxLayout(phrases_container)
        phrases_layout.setContentsMargins(5, 5, 5, 5)
        phrases_layout.setSpacing(5)
        
        phrases_scroll.setWidget(phrases_container)
        layout.addWidget(phrases_scroll)

        # Раздел: Документы закупки
        layout.addStretch()
        
        documents_label = DocumentsTabBuilder._make_section_label("📄 Документы закупки")
        layout.addWidget(documents_label)
        
        # Кнопка для открытия диалога с документами
        open_documents_btn = QPushButton("📄 Открыть документы закупки")
        apply_button_style(open_documents_btn, "primary")
        open_documents_btn.setFixedHeight(50)
        layout.addWidget(open_documents_btn)
        
        return {
            'phrases_container': phrases_container,
            'phrases_layout': phrases_layout,
            'open_documents_btn': open_documents_btn,
        }
    
    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        """Создание заголовка секции."""
        label = QLabel(text)
        apply_label_style(label, "h3")
        return label

