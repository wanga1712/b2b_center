"""
MODULE: modules.crm.sales_funnel.deal_detail_logic.documents_handler
RESPONSIBILITY: Manage document tab in Deal Card (display phrases, download files).
ALLOWED: PyQt5, urllib, os, loguru, typing.
FORBIDDEN: Heavy processing in UI thread (use thread pool if needed).
ERRORS: None.

Модуль для работы с документами закупки в детальной карточке сделки.

Содержит методы для скачивания документов и отображения найденных фраз.
"""

import os
import urllib.request
from typing import List, Dict, Any
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, QDialog, QTableWidget, 
                             QTableWidgetItem, QHBoxLayout, QPushButton, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt
from loguru import logger

from modules.styles.general_styles import apply_button_style, apply_label_style, COLORS


class DocumentsHandler:
    """Класс для обработки документов закупки."""
    
    def __init__(self, phrases_container: QWidget, phrases_layout: QVBoxLayout, 
                 open_documents_btn: QPushButton, parent_dialog):
        self.phrases_container = phrases_container
        self.phrases_layout = phrases_layout
        self.open_documents_btn = open_documents_btn
        self.parent_dialog = parent_dialog
        self.document_links = []
    
    def fill_documents(self, data: Dict[str, Any]) -> None:
        """Заполнение вкладки 'Документы закупки' найденными фразами и ссылками."""
        estimate_items = data.get("estimate_items", [])
        document_links_data = data.get("document_links", [])
        
        logger.info(f"DocumentsHandler.fill_documents: estimate_items count={len(estimate_items)}, document_links count={len(document_links_data)}")
        
        # Очищаем предыдущие фразы
        while self.phrases_layout.count():
            item = self.phrases_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Заполняем найденные фразы (карточки)
        for item in estimate_items:
            self._add_phrase_card(item)
        
        # Если нет фраз
        if not estimate_items:
            no_phrases_label = QLabel("Найденные фразы отсутствуют")
            no_phrases_label.setStyleSheet(f"color: {COLORS['text_light']}; padding: 10px;")
            self.phrases_layout.addWidget(no_phrases_label)
        
        # Сохраняем ссылки на документы
        self.document_links = []
        for doc_link in document_links_data:
            doc_url = doc_link.get("document_links", "")
            file_name = doc_link.get("file_name", "Документ")
            self.document_links.append({"url": doc_url, "name": file_name})
        
        # Обновляем текст кнопки
        if self.open_documents_btn:
            doc_count = len(self.document_links)
            if doc_count > 0:
                self.open_documents_btn.setText(f"📄 Открыть документы закупки ({doc_count})")
                self.open_documents_btn.setEnabled(True)
            else:
                self.open_documents_btn.setText("📄 Документы отсутствуют")
                self.open_documents_btn.setEnabled(False)
    
    def _add_phrase_card(self, item: Dict[str, Any]) -> None:
        """Создание карточки для найденной фразы."""
        product_name = item.get("product_name", "")
        score = item.get("score", 0)
        source_file = item.get("source_file", "")
        cell_address = item.get("cell_address", "")
        matched_text = item.get("matched_display_text") or item.get("matched_text", "")
        
        # Определяем цвет на основе точности
        if score >= 90:
            color = "#4CAF50"  # Зеленый
            text_color = "#1B5E20"
        elif score >= 75:
            color = "#8BC34A"  # Светло-зеленый
            text_color = "#33691E"
        elif score >= 60:
            color = "#FFC107"  # Желтый
            text_color = "#F57F17"
        else:
            color = "#F44336"  # Красный
            text_color = "#B71C1C"
        
        # Создаем карточку
        phrase_card = QFrame()
        phrase_card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-left: 5px solid {color};
                border-radius: 3px;
                padding: 8px;
            }}
        """)
        
        card_layout = QVBoxLayout(phrase_card)
        card_layout.setContentsMargins(5, 5, 5, 5)
        card_layout.setSpacing(3)
        
        # Наименование товара
        name_label = QLabel(f"<b>{product_name}</b>")
        name_label.setWordWrap(True)
        card_layout.addWidget(name_label)
        
        # Найденный текст
        if matched_text:
            matched_label = QLabel(f"📝 Найдено: \"{matched_text}\"")
            matched_label.setWordWrap(True)
            matched_label.setStyleSheet(f"color: {COLORS['text_dark']}; font-size: 11px; font-style: italic; padding: 3px 0px;")
            card_layout.addWidget(matched_label)
        
        # Файл и ячейка
        file_name = os.path.basename(source_file) if source_file else "Неизвестный файл"
        location_text = f"📄 {file_name}"
        if cell_address:
            location_text += f" • Ячейка: {cell_address}"
        location_label = QLabel(location_text)
        location_label.setStyleSheet(f"color: {COLORS['text_light']}; font-size: 11px;")
        card_layout.addWidget(location_label)
        
        # Точность
        score_label = QLabel(f"Точность: {score:.1f}%")
        score_label.setStyleSheet(f"color: {text_color}; font-weight: bold; font-size: 12px;")
        card_layout.addWidget(score_label)
        
        self.phrases_layout.addWidget(phrase_card)
    
    def open_documents_dialog(self) -> None:
        """Открытие диалога со списком документов для скачивания."""
        if not self.document_links:
            QMessageBox.information(self.parent_dialog, "Информация", "Документы отсутствуют")
            return
        
        dialog = QDialog(self.parent_dialog)
        dialog.setWindowTitle("Документы закупки")
        dialog.resize(700, 500)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Заголовок
        title_label = QLabel(f"<h3>📄 Документы закупки ({len(self.document_links)} файлов)</h3>")
        layout.addWidget(title_label)
        
        # Таблица документов
        docs_table = QTableWidget()
        docs_table.setColumnCount(2)
        docs_table.setHorizontalHeaderLabels(["Название файла", "Действие"])
        docs_table.horizontalHeader().setStretchLastSection(False)
        docs_table.horizontalHeader().setSectionResizeMode(0, docs_table.horizontalHeader().Stretch)
        docs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        docs_table.setSelectionBehavior(QTableWidget.SelectRows)
        docs_table.setRowCount(len(self.document_links))
        
        # Заполняем таблицу
        for idx, doc in enumerate(self.document_links):
            # Название файла
            name_item = QTableWidgetItem(f"📄 {doc['name']}")
            docs_table.setItem(idx, 0, name_item)
            
            # Кнопка скачивания
            download_btn = QPushButton("⬇ Скачать")
            apply_button_style(download_btn, "secondary")
            download_btn.clicked.connect(lambda checked, url=doc['url'], name=doc['name']: self.download_document(url, name))
            docs_table.setCellWidget(idx, 1, download_btn)
        
        layout.addWidget(docs_table)
        
        # Кнопки внизу
        buttons_layout = QHBoxLayout()
        
        download_all_btn = QPushButton("⬇ Скачать все")
        apply_button_style(download_all_btn, "primary")
        download_all_btn.clicked.connect(self.download_all_documents)
        buttons_layout.addWidget(download_all_btn)
        
        close_btn = QPushButton("Закрыть")
        apply_button_style(close_btn, "secondary")
        close_btn.clicked.connect(dialog.close)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
        dialog.exec_()
    
    def download_document(self, url: str, file_name: str) -> None:
        """Скачивание одного документа."""
        try:
            # Предлагаем пользователю выбрать место сохранения
            save_path, _ = QFileDialog.getSaveFileName(
                self.parent_dialog,
                "Сохранить документ",
                file_name,
                "Все файлы (*.*)"
            )
            
            if save_path:
                logger.info(f"Скачивание документа: {url} -> {save_path}")
                urllib.request.urlretrieve(url, save_path)
                QMessageBox.information(self.parent_dialog, "Успех", f"Документ '{file_name}' успешно скачан!")
        except Exception as exc:
            logger.error(f"Ошибка при скачивании документа {file_name}: {exc}", exc_info=True)
            QMessageBox.critical(self.parent_dialog, "Ошибка", f"Не удалось скачать документ '{file_name}': {exc}")
    
    def download_all_documents(self) -> None:
        """Скачивание всех документов."""
        try:
            if not self.document_links:
                QMessageBox.warning(self.parent_dialog, "Предупреждение", "Нет документов для скачивания")
                return
            
            # Предлагаем пользователю выбрать папку
            save_dir = QFileDialog.getExistingDirectory(
                self.parent_dialog,
                "Выберите папку для сохранения документов"
            )
            
            if save_dir:
                success_count = 0
                failed_count = 0
                
                for doc in self.document_links:
                    try:
                        url = doc["url"]
                        file_name = doc["name"]
                        save_path = os.path.join(save_dir, file_name)
                        
                        logger.info(f"Скачивание документа: {url} -> {save_path}")
                        urllib.request.urlretrieve(url, save_path)
                        success_count += 1
                    except Exception as exc:
                        logger.error(f"Ошибка при скачивании документа {doc['name']}: {exc}")
                        failed_count += 1
                
                msg = f"Скачано: {success_count} документов"
                if failed_count > 0:
                    msg += f"\nОшибки: {failed_count} документов"
                
                QMessageBox.information(self.parent_dialog, "Результат скачивания", msg)
        except Exception as exc:
            logger.error(f"Ошибка при скачивании всех документов: {exc}", exc_info=True)
            QMessageBox.critical(self.parent_dialog, "Ошибка", f"Не удалось скачать документы: {exc}")

