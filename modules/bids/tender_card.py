"""
Виджет карточки торгов (сокращенный и полный вид)

Карточка отображает информацию о торге:
- Сокращенный вид: основная информация
- Полный вид: вся информация при двойном клике
"""

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog,
    QScrollArea, QWidget, QTextEdit, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QThread
from PyQt5.QtGui import QFont, QDesktopServices
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
from pathlib import Path
from loguru import logger

from modules.styles.general_styles import (
    COLORS, FONT_SIZES, SIZES, apply_label_style, apply_button_style,
    apply_text_style_light, apply_text_style_primary, apply_font_weight
)
from core.exceptions import DocumentSearchError

if TYPE_CHECKING:
    from services.document_search_service import DocumentSearchService
    from services.archive_processing_service import ArchiveProcessingService
    from modules.bids.document_search_result_dialog import DocumentSearchResultDialog

from modules.bids.document_search_progress_dialog import DocumentSearchProgressDialog


class TenderCard(QFrame):
    """
    Карточка торгов (сокращенный вид)
    
    Отображает основную информацию о торге.
    При двойном клике открывается диалог с полной информацией.
    """
    
    def __init__(
        self,
        tender_data: Dict[str, Any],
        document_search_service: Optional['DocumentSearchService'] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.tender_data = tender_data or {}
        self.document_search_service = document_search_service
        try:
            self.init_ui()
        except Exception as e:
            from loguru import logger
            logger.error(f"Ошибка при инициализации карточки торга ID {tender_data.get('id', 'неизвестно')}: {e}")
            raise
    
    def init_ui(self):
        """Инициализация интерфейса карточки"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Стиль карточки
        self.setStyleSheet(f"""
            TenderCard {{
                background: {COLORS['white']};
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
                min-height: 120px;
            }}
            TenderCard:hover {{
                border: 2px solid {COLORS['primary']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }}
        """)
        
        # Название торгов
        auction_name = self.tender_data.get('auction_name', 'Без названия')
        name_label = QLabel(auction_name)
        apply_label_style(name_label, 'h3')
        name_label.setWordWrap(True)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_dark']};
                font-weight: bold;
                margin-bottom: 5px;
            }}
        """)
        layout.addWidget(name_label)
        
        # Информация в одну строку
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)
        
        # Номер контракта
        contract_number = self.tender_data.get('contract_number', '')
        if contract_number:
            contract_label = QLabel(f"№ {contract_number}")
            apply_label_style(contract_label, 'small')
            apply_text_style_light(contract_label)
            info_layout.addWidget(contract_label)
        
        # Регион
        region_name = self.tender_data.get('region_name') or self.tender_data.get('delivery_region', '')
        if region_name:
            region_label = QLabel(f"📍 {region_name}")
            apply_label_style(region_label, 'small')
            apply_text_style_light(region_label)
            info_layout.addWidget(region_label)
        
        # Заказчик
        customer_name = (
            self.tender_data.get('customer_short_name') or 
            self.tender_data.get('customer_full_name', '')
        )
        if customer_name:
            customer_label = QLabel(f"👤 {customer_name[:50]}")
            apply_label_style(customer_label, 'small')
            apply_text_style_light(customer_label)
            customer_label.setToolTip(customer_name)
            info_layout.addWidget(customer_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Цена и даты
        price_date_layout = QHBoxLayout()
        price_date_layout.setSpacing(15)
        
        # Начальная цена
        initial_price = self.tender_data.get('initial_price')
        if initial_price:
            price_str = f"{float(initial_price):,.0f}".replace(',', ' ')
            price_label = QLabel(f"💰 {price_str} ₽")
            apply_label_style(price_label, 'normal')
            apply_text_style_primary(price_label)
            apply_font_weight(price_label)
            price_date_layout.addWidget(price_label)
        
        # Дата окончания
        end_date = self.tender_data.get('end_date')
        if end_date:
            if isinstance(end_date, str):
                try:
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                except:
                    pass
            if hasattr(end_date, 'strftime'):
                date_str = end_date.strftime('%d.%m.%Y')
                date_label = QLabel(f"📅 До {date_str}")
                apply_label_style(date_label, 'small')
                apply_text_style_light(date_label)
                price_date_layout.addWidget(date_label)
        
        price_date_layout.addStretch()
        layout.addLayout(price_date_layout)
        
        # ОКПД код
        okpd_code = (
            self.tender_data.get('okpd_sub_code') or 
            self.tender_data.get('okpd_main_code', '')
        )
        if okpd_code:
            okpd_label = QLabel(f"ОКПД: {okpd_code}")
            apply_label_style(okpd_label, 'small')
            apply_text_style_light(okpd_label)
            layout.addWidget(okpd_label)
        
        # Кнопка открытия ссылки
        if self.tender_data.get('tender_link'):
            btn_link = QPushButton("🔗 Открыть торг")
            apply_button_style(btn_link, 'outline')
            btn_link.setMaximumWidth(150)
            btn_link.clicked.connect(self.open_tender_link)
            layout.addWidget(btn_link)
        
        # Включаем обработку двойного клика
        self.setMouseTracking(True)
    
    def mouseDoubleClickEvent(self, event):
        """Обработка двойного клика - открытие полной информации"""
        super().mouseDoubleClickEvent(event)
        dialog = TenderDetailDialog(
            self.tender_data,
            document_search_service=self.document_search_service,
            parent=self,
        )
        dialog.exec_()
    
    def open_tender_link(self):
        """Открытие ссылки на торг в браузере"""
        link = self.tender_data.get('tender_link')
        if link:
            QDesktopServices.openUrl(QUrl(link))


class TenderDetailDialog(QDialog):
    """
    Диалог с полной информацией о торге
    """
    
    def __init__(
        self,
        tender_data: Dict[str, Any],
        document_search_service: Optional['DocumentSearchService'] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.tender_data = tender_data
        self.document_search_service = document_search_service
        self._document_search_worker: Optional['DocumentSearchWorker'] = None
        from modules.styles.ui_config import configure_dialog
        configure_dialog(self, "Подробная информация о торге", size_preset="tender_detail")
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса диалога"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Прокручиваемая область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
                background: {COLORS['white']};
            }}
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        # Название
        auction_name = self.tender_data.get('auction_name', 'Без названия')
        name_label = QLabel(auction_name)
        apply_label_style(name_label, 'h1')
        name_label.setWordWrap(True)
        content_layout.addWidget(name_label)
        
        # Разделитель
        content_layout.addWidget(self._create_separator())
        
        # Основная информация
        content_layout.addWidget(self._create_info_section("Основная информация", [
            ("Номер контракта", self.tender_data.get('contract_number')),
            ("Площадка", self.tender_data.get('platform_name')),
            ("Регион", self.tender_data.get('region_name') or self.tender_data.get('delivery_region')),
        ]))
        
        # Заказчик и подрядчик
        content_layout.addWidget(self._create_info_section("Участники", [
            ("Заказчик", self.tender_data.get('customer_full_name') or self.tender_data.get('customer_short_name')),
            ("Подрядчик", self.tender_data.get('contractor_full_name') or self.tender_data.get('contractor_short_name')),
        ]))
        
        # ОКПД
        okpd_code = (
            self.tender_data.get('okpd_sub_code') or 
            self.tender_data.get('okpd_main_code', '')
        )
        okpd_name = self.tender_data.get('okpd_name', '')
        if okpd_code:
            content_layout.addWidget(self._create_info_section("ОКПД", [
                ("Код", okpd_code),
                ("Название", okpd_name),
            ]))
        
        # Цены
        content_layout.addWidget(self._create_info_section("Финансы", [
            ("Начальная цена", self._format_price(self.tender_data.get('initial_price'))),
            ("Финальная цена", self._format_price(self.tender_data.get('final_price'))),
            ("Сумма обеспечения", self._format_price(self.tender_data.get('guarantee_amount'))),
        ]))
        
        # Даты
        content_layout.addWidget(self._create_info_section("Даты", [
            ("Дата начала", self._format_date(self.tender_data.get('start_date'))),
            ("Дата окончания", self._format_date(self.tender_data.get('end_date'))),
            ("Начало поставки", self._format_date(self.tender_data.get('delivery_start_date'))),
            ("Конец поставки", self._format_date(self.tender_data.get('delivery_end_date'))),
        ]))
        
        # Доставка
        delivery_region = self.tender_data.get('delivery_region')
        delivery_address = self.tender_data.get('delivery_address')
        if delivery_region or delivery_address:
            content_layout.addWidget(self._create_info_section("Доставка", [
                ("Регион доставки", delivery_region),
                ("Адрес доставки", delivery_address),
            ]))
        
        # Ссылки на документы
        document_links = self.tender_data.get('document_links', [])
        if document_links:
            content_layout.addWidget(self._create_documents_section(document_links))
        
        # Кнопка поиска по документации
        self._add_document_search_button(layout)

        # Ссылка на торг
        tender_link = self.tender_data.get('tender_link')
        if tender_link:
            btn_link = QPushButton("🔗 Открыть торг в браузере")
            apply_button_style(btn_link, 'primary')
            btn_link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(tender_link)))
            content_layout.addWidget(btn_link)
        
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Кнопка закрытия
        btn_close = QPushButton("Закрыть")
        apply_button_style(btn_close, 'secondary')
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _add_document_search_button(self, layout: QVBoxLayout) -> None:
        """Добавление кнопки поиска документации."""
        logger.info("Инициализация кнопки поиска по документации")
        self.btn_doc_search = QPushButton("🔍 Поиск по документации")
        apply_button_style(self.btn_doc_search, 'primary')
        has_documents = bool(self.tender_data.get('document_links'))
        self.btn_doc_search.setEnabled(has_documents)
        self.btn_doc_search.clicked.connect(self.handleDocumentationSearch)
        layout.addWidget(self.btn_doc_search)
        if not has_documents:
            self.btn_doc_search.setToolTip("Нет приложенных документов для анализа.")

    def handleDocumentationSearch(self):
        """Обработка клика по кнопке поиска документации."""
        logger.info("handleDocumentationSearch вызван")
        if not self.document_search_service:
            QMessageBox.warning(
                self,
                "Поиск по документации",
                "Сервис поиска по документации недоступен.",
            )
            return

        documents = self.tender_data.get('document_links', [])
        if not documents:
            QMessageBox.information(
                self,
                "Поиск по документации",
                "Для данного торга нет документов.",
            )
            return

        # Создаем диалог прогресса
        progress_dialog = DocumentSearchProgressDialog(self)
        
        # Создаем worker thread для выполнения поиска
        self._document_search_worker = DocumentSearchWorker(
            self.document_search_service,
            documents,
            self.tender_data.get('id'),
            self._determine_registry_type(),
        )
        
        # Подключаем сигналы для обновления прогресса
        self._document_search_worker.progress_updated.connect(progress_dialog.set_stage)
        self._document_search_worker.finished.connect(
            lambda result: self._on_search_finished(result, progress_dialog),
        )
        self._document_search_worker.error_occurred.connect(
            lambda error: self._on_search_error(error, progress_dialog),
        )
        progress_dialog.cancelled.connect(self._document_search_worker.cancel)
        
        # Запускаем worker
        self._document_search_worker.start()
        
        # Показываем диалог (блокирующий)
        progress_dialog.exec_()
        
        self._finalize_document_search_worker()
    
    def _on_search_finished(self, result: Dict[str, Any], progress_dialog: DocumentSearchProgressDialog):
        """Обработка завершения поиска"""
        logger.info("Поиск завершен, закрываю диалог прогресса и показываю результаты")
        # Убеждаемся, что прогресс доходит до 100%
        progress_dialog.set_stage("Завершено", 100, "Обработка завершена")
        # Даем время на обновление UI
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        # Закрываем диалог
        progress_dialog.accept()
        # Показываем результаты
        self._show_document_search_results(result)
    
    def _on_search_error(self, error: str, progress_dialog: DocumentSearchProgressDialog):
        """Обработка ошибки поиска"""
        progress_dialog.reject()
        if isinstance(error, DocumentSearchError):
            QMessageBox.information(self, "Поиск по документации", str(error))
        else:
            logger.exception("Ошибка поиска по документации")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось выполнить поиск по документации:\n{error}",
            )
    
    def _show_document_search_results(self, result: Dict[str, Any]) -> None:
        """Отображение результатов поиска."""
        try:
            logger.info("Отображение результатов поиска по документации")
            
            # Проверяем и валидируем данные
            if not result:
                logger.error("Результат поиска пуст")
                QMessageBox.warning(self, "Результаты поиска", "Результаты поиска не получены.")
                return
            
            matches = result.get("matches", [])
            if not isinstance(matches, list):
                logger.error(f"Неверный формат matches: {type(matches)}")
                matches = []
            
            logger.debug(f"Найдено совпадений для отображения: {len(matches)}")
            
            try:
                grouped = ArchiveProcessingService.group_matches_by_score(matches)
            except Exception as e:
                logger.error(f"Ошибка группировки совпадений: {e}", exc_info=True)
                grouped = {"exact": [], "good": []}
            
            tender_folder = result.get("tender_folder")
            if not tender_folder:
                tender_folder = self.document_search_service.download_dir
            tender_folder = Path(tender_folder)
            
            download_root = self.document_search_service.download_dir
            if not download_root:
                logger.error("download_dir не установлен")
                QMessageBox.warning(self, "Ошибка", "Не удалось определить директорию загрузки.")
                return
            
            logger.debug(f"Создание диалога результатов: совпадений={len(matches)}, папка={tender_folder}")
            
            dialog = DocumentSearchResultDialog(
                self,
                grouped_matches=grouped,
                tender_folder=tender_folder,
                download_root=download_root,
            )
            logger.debug("Диалог результатов создан, показываю")
            dialog.exec_()
            logger.debug("Диалог результатов закрыт")
        except Exception as e:
            logger.exception("Критическая ошибка при отображении результатов поиска")
            QMessageBox.critical(
                self,
                "Ошибка отображения результатов",
                f"Не удалось отобразить результаты поиска:\n{str(e)}\n\nПроверьте логи для подробностей.",
            )
    
    def _finalize_document_search_worker(self) -> None:
        """Гарантирует корректное завершение worker-потока."""
        if not self._document_search_worker:
            return

        worker = self._document_search_worker
        if worker.isRunning():
            worker.requestInterruption()
            worker.wait()
        else:
            worker.wait()

        self._document_search_worker = None
    
    def _determine_registry_type(self) -> str:
        """Определяет тип реестра (44ФЗ/223ФЗ) для именования папок."""
        raw_value = (
            self.tender_data.get('registry_type')
            or self.tender_data.get('law')
            or ''
        )
        value = str(raw_value).lower()
        if '223' in value:
            return '223fz'
        return '44fz'
    
    def _create_separator(self) -> QFrame:
        """Создание разделителя"""
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"color: {COLORS['border']};")
        return separator
    
    def _create_info_section(self, title: str, items: list) -> QWidget:
        """Создание секции с информацией"""
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['secondary']};
                border-radius: {SIZES['border_radius_normal']}px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(section)
        layout.setSpacing(8)
        
        # Заголовок секции
        title_label = QLabel(title)
        apply_label_style(title_label, 'h2')
        layout.addWidget(title_label)
        
        # Элементы
        for label, value in items:
            if value:
                item_layout = QHBoxLayout()
                label_widget = QLabel(f"{label}:")
                apply_label_style(label_widget, 'normal')
                apply_text_style_light(label_widget)
                label_widget.setStyleSheet(label_widget.styleSheet() + " min-width: 150px;")
                item_layout.addWidget(label_widget)
                
                value_widget = QLabel(str(value))
                value_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
                apply_label_style(value_widget, 'normal')
                value_widget.setWordWrap(True)
                item_layout.addWidget(value_widget)
                layout.addLayout(item_layout)
        
        return section
    
    def _create_documents_section(self, document_links: list) -> QWidget:
        """Создание секции со ссылками на документы"""
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['secondary']};
                border-radius: {SIZES['border_radius_normal']}px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(section)
        layout.setSpacing(8)
        
        title_label = QLabel("Документы")
        apply_label_style(title_label, 'h2')
        layout.addWidget(title_label)
        
        for doc in document_links:
            doc_link = doc.get('document_links', '')
            file_name = doc.get('file_name', 'Документ')
            if doc_link:
                btn_doc = QPushButton(f"📄 {file_name}")
                apply_button_style(btn_doc, 'outline')
                btn_doc.clicked.connect(lambda checked, link=doc_link: QDesktopServices.openUrl(QUrl(link)))
                layout.addWidget(btn_doc)
        
        return section
    
    def _format_price(self, price: Optional[Any]) -> str:
        """Форматирование цены"""
        if not price:
            return "—"
        try:
            return f"{float(price):,.0f} ₽".replace(',', ' ')
        except:
            return str(price)
    
    def _format_date(self, date_value: Optional[Any]) -> str:
        """Форматирование даты"""
        if not date_value:
            return "—"
        try:
            if isinstance(date_value, str):
                date_value = datetime.strptime(date_value, '%Y-%m-%d').date()
            if hasattr(date_value, 'strftime'):
                return date_value.strftime('%d.%m.%Y')
            return str(date_value)
        except:
            return str(date_value) if date_value else "—"


class DocumentSearchWorker(QThread):
    """Worker thread для выполнения поиска по документации в фоне"""
    
    progress_updated = pyqtSignal(str, int, str)  # stage, progress, detail
    finished = pyqtSignal(dict)  # result
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(
        self,
        document_search_service: 'DocumentSearchService',
        documents: list,
        tender_id: Optional[int],
        registry_type: str,
    ):
        super().__init__()
        self.document_search_service = document_search_service
        self.documents = documents
        self.tender_id = tender_id
        self.registry_type = registry_type
        self._cancelled = False
        self._previous_progress_callback = document_search_service.progress_callback
        
        # Устанавливаем callback для обновления прогресса
        self.document_search_service.progress_callback = self._update_progress
    
    def _update_progress(self, stage: str, progress: int, detail: Optional[str] = None):
        """Callback для обновления прогресса"""
        if not self._cancelled:
            logger.debug(f"Обновление прогресса: {stage} - {progress}% - {detail or ''}")
            self.progress_updated.emit(stage, progress, detail or "")
    
    def cancel(self):
        """Отмена операции"""
        self._cancelled = True
    
    def run(self):
        """Выполнение поиска в фоновом потоке"""
        try:
            result = self.document_search_service.run_document_search(
                self.documents,
                tender_id=self.tender_id,
                registry_type=self.registry_type,
            )
            if not self._cancelled:
                self.finished.emit(result)
        except Exception as error:
            if not self._cancelled:
                self.error_occurred.emit(str(error))
        finally:
            if self.document_search_service.progress_callback is self._update_progress:
                self.document_search_service.progress_callback = self._previous_progress_callback

