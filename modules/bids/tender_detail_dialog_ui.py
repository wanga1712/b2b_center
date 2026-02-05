"""
MODULE: modules.bids.tender_detail_dialog_ui
RESPONSIBILITY: Create UI elements for detail dialog.
ALLOWED: PyQt5, modules.styles.*, modules.bids.tender_card_utils.
FORBIDDEN: Business logic.
ERRORS: None.

Модуль для создания UI элементов диалога деталей закупки.
"""

from typing import Any, Dict, List
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl
from modules.styles.general_styles import (
    apply_label_style, apply_button_style, apply_text_style_light,
    apply_frame_style, apply_separator_style
)
from modules.bids.tender_card_utils import format_balance_holder, build_link_label
from modules.bids.tender_match_details import create_match_summary_block, create_match_details_block


def create_separator() -> QFrame:
    """Создание разделителя"""
    separator = QFrame()
    separator.setFrameShape(QFrame.HLine)
    apply_separator_style(separator, 'border')
    return separator


def create_info_section(title: str, items: list) -> QWidget:
    """Создание секции с информацией"""
    section = QFrame()
    apply_frame_style(section, 'secondary')
    layout = QVBoxLayout(section)
    layout.setSpacing(8)
    
    title_label = QLabel(title)
    apply_label_style(title_label, 'h2')
    layout.addWidget(title_label)
    
    for label, value in items:
        if value:
            item_layout = QHBoxLayout()
            label_widget = QLabel(f"{label}:")
            apply_label_style(label_widget, 'normal')
            apply_text_style_light(label_widget)
            label_widget.setMinimumWidth(150)
            item_layout.addWidget(label_widget)
            
            value_widget = QLabel(str(value))
            value_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
            apply_label_style(value_widget, 'normal')
            value_widget.setWordWrap(True)
            item_layout.addWidget(value_widget)
            layout.addLayout(item_layout)
    
    return section


def create_documents_section(document_links: list, download_handler) -> QWidget:
    """Создание секции со ссылками на документы"""
    section = QFrame()
    apply_frame_style(section, 'secondary')
    layout = QVBoxLayout(section)
    layout.setSpacing(8)
    
    header_layout = QHBoxLayout()
    title_label = QLabel("Документы")
    apply_label_style(title_label, 'h2')
    header_layout.addWidget(title_label)
    header_layout.addStretch()
    
    if document_links:
        btn_download_all = QPushButton("⬇️ Скачать все документы")
        apply_button_style(btn_download_all, 'primary')
        btn_download_all.clicked.connect(lambda: download_handler(document_links))
        header_layout.addWidget(btn_download_all)
    
    layout.addLayout(header_layout)
    
    for doc in document_links:
        doc_link = doc.get('document_links', '')
        file_name = doc.get('file_name', 'Документ')
        if doc_link:
            btn_doc = QPushButton(f"📄 {file_name}")
            apply_button_style(btn_doc, 'outline')
            btn_doc.clicked.connect(lambda checked, link=doc_link: QDesktopServices.openUrl(QUrl(link)))
            layout.addWidget(btn_doc)
    
    return section


def create_match_column(match_summary, match_details) -> QWidget:
    """Создает правую колонку с результатами поиска"""
    from typing import Optional
    if not match_summary and not match_details:
        return None
    
    column = QFrame()
    apply_frame_style(column, 'secondary')
    layout = QVBoxLayout(column)
    layout.setSpacing(12)
    layout.addWidget(create_match_summary_block(match_summary))
    layout.addWidget(create_match_details_block(match_details or []))
    layout.addStretch()
    return column

