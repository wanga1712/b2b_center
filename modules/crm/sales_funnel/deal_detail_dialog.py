"""
MODULE: modules.crm.sales_funnel.deal_detail_dialog
RESPONSIBILITY: Detailed deal dialog UI window.
ALLOWED: PyQt5, loguru, modules.styles.*, modules.crm.sales_funnel.models, modules.crm.sales_funnel.deal_detail_service, modules.crm.sales_funnel.deal_detail_logic.*, modules.crm.sales_funnel.deal_detail_ui.*.
FORBIDDEN: Heavy business logic (delegate to service).
ERRORS: None.

Диалоговая форма детальной карточки сделки (воронка продаж).

Основной класс, использующий модули из deal_detail_ui/ и deal_detail_logic/.
"""

from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QWidget,
    QTableWidget,
    QTextEdit,
    QPushButton,
)
from PyQt5.QtCore import Qt

from loguru import logger
from modules.styles.general_styles import apply_label_style, apply_button_style, COLORS
from modules.crm.sales_funnel.models import Deal
from modules.crm.sales_funnel.deal_detail_service import DealDetailService

# Импортируем наши новые модули
from modules.crm.sales_funnel.deal_detail_logic.data_fillers import DealDataFillers
from modules.crm.sales_funnel.deal_detail_logic.materials_handler import MaterialsHandler
from modules.crm.sales_funnel.deal_detail_logic.works_handler import WorksHandler
from modules.crm.sales_funnel.deal_detail_logic.products_handler import ProductsHandler
from modules.crm.sales_funnel.deal_detail_logic.documents_handler import DocumentsHandler
from modules.crm.sales_funnel.deal_detail_ui.tab_items_builder import ItemsTabBuilder
from modules.crm.sales_funnel.deal_detail_ui.tab_documents_builder import DocumentsTabBuilder


class DealDetailDialog(QDialog):
    """Окно детальной карточки сделки."""

    def __init__(self, deal: Deal, detail_service: DealDetailService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.deal = deal
        self.detail_service = detail_service
        self.data: Dict[str, Any] = {}
        self.setWindowTitle(f"Карточка сделки — {deal.name}")
        self.resize(900, 700)
        
        # Обработчики будут созданы после инициализации UI
        self.materials_handler: Optional[MaterialsHandler] = None
        self.works_handler: Optional[WorksHandler] = None
        self.products_handler: Optional[ProductsHandler] = None
        self.documents_handler: Optional[DocumentsHandler] = None
        
        self._init_ui()
        self._load_data()

    def _init_ui(self) -> None:
        """Инициализация пользовательского интерфейса."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Заголовок диалога
        self.title_label = QLabel(f"Сделка: {self.deal.name}")
        apply_label_style(self.title_label, "h2")
        main_layout.addWidget(self.title_label)

        # Summary-блок
        self._build_summary_block(main_layout)

        # Вкладки
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Создаем вкладки
        self.tab_overview = QWidget()
        self.tab_customer = QWidget()
        self.tab_contractor = QWidget()
        self.tab_items = QWidget()
        self.tab_documents = QWidget()

        self.tabs.addTab(self.tab_overview, "Общая информация")
        self.tabs.addTab(self.tab_customer, "Заказчик")
        self.tabs.addTab(self.tab_contractor, "Подрядчик")
        self.tabs.addTab(self.tab_items, "КП / Товары")
        self.tabs.addTab(self.tab_documents, "📄 Документы закупки")

        # Кнопка закрытия
        btn_close = QPushButton("Закрыть")
        apply_button_style(btn_close, "secondary")
        btn_close.clicked.connect(self.accept)
        main_layout.addWidget(btn_close, alignment=Qt.AlignRight)

        # Инициализируем вкладки
        self._init_overview_tab()
        self._init_customer_tab()
        self._init_contractor_tab()
        self._init_items_tab()
        self._init_documents_tab()

    def _build_summary_block(self, parent_layout: QVBoxLayout) -> None:
        """Построение summary-блока с ключевой информацией."""
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(16)

        # Левая колонка
        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        self.summary_amount_label = QLabel()
        apply_label_style(self.summary_amount_label, "normal")
        left_col.addWidget(self.summary_amount_label)

        self.summary_deal_kp_label = QLabel()
        apply_label_style(self.summary_deal_kp_label, "normal")
        left_col.addWidget(self.summary_deal_kp_label)

        self.summary_margin_label = QLabel()
        apply_label_style(self.summary_margin_label, "normal")
        left_col.addWidget(self.summary_margin_label)

        self.summary_status_label = QLabel()
        apply_label_style(self.summary_status_label, "normal")
        left_col.addWidget(self.summary_status_label)

        self.summary_stage_label = QLabel()
        apply_label_style(self.summary_stage_label, "normal")
        left_col.addWidget(self.summary_stage_label)

        self.summary_delivery_label = QLabel()
        apply_label_style(self.summary_delivery_label, "normal")
        left_col.addWidget(self.summary_delivery_label)

        # Правая колонка
        right_col = QVBoxLayout()
        right_col.setSpacing(4)

        self.summary_registry_label = QLabel()
        apply_label_style(self.summary_registry_label, "normal")
        right_col.addWidget(self.summary_registry_label)

        self.summary_tender_number_label = QLabel()
        apply_label_style(self.summary_tender_number_label, "normal")
        right_col.addWidget(self.summary_tender_number_label)

        self.summary_owner_label = QLabel()
        apply_label_style(self.summary_owner_label, "normal")
        right_col.addWidget(self.summary_owner_label)

        self.summary_region_label = QLabel()
        apply_label_style(self.summary_region_label, "normal")
        right_col.addWidget(self.summary_region_label)

        summary_layout.addLayout(left_col)
        summary_layout.addLayout(right_col)
        parent_layout.addLayout(summary_layout)

    def _init_overview_tab(self) -> None:
        """Инициализация вкладки 'Общая информация'."""
        layout = QVBoxLayout(self.tab_overview)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.tender_info = QTextEdit()
        self.tender_info.setReadOnly(True)
        layout.addWidget(self._make_section_label("Закупка"))
        layout.addWidget(self.tender_info)

        # Ссылка на закупку
        self.tender_link_label = QLabel()
        apply_label_style(self.tender_link_label, "small")
        self.tender_link_label.setTextFormat(Qt.RichText)
        self.tender_link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.tender_link_label.setOpenExternalLinks(True)
        self.tender_link_label.hide()
        layout.addWidget(self.tender_link_label)

        # Чат загружается в _load_data()
        self.chat_widget = None

    def _init_customer_tab(self) -> None:
        """Инициализация вкладки 'Заказчик'."""
        layout = QVBoxLayout(self.tab_customer)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.customer_info = QTextEdit()
        self.customer_info.setReadOnly(True)
        layout.addWidget(self._make_section_label("Заказчик"))
        layout.addWidget(self.customer_info)

        self.customer_contacts_table = self._create_contacts_table()
        layout.addWidget(self._make_section_label("Контакты заказчика"))
        layout.addWidget(self.customer_contacts_table)

    def _init_contractor_tab(self) -> None:
        """Инициализация вкладки 'Подрядчик'."""
        layout = QVBoxLayout(self.tab_contractor)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.contractor_info = QTextEdit()
        self.contractor_info.setReadOnly(True)
        layout.addWidget(self._make_section_label("Подрядчик"))
        layout.addWidget(self.contractor_info)

        self.contractor_contacts_table = self._create_contacts_table()
        layout.addWidget(self._make_section_label("Контакты подрядчика"))
        layout.addWidget(self.contractor_contacts_table)

    def _init_items_tab(self) -> None:
        """Инициализация вкладки 'КП / Товары'."""
        # Используем UI билдер
        widgets = ItemsTabBuilder.build_items_tab(self.tab_items)
        
        # Сохраняем ссылки на виджеты
        self.products_table = widgets['products_table']
        self.products_total_label = widgets['products_total_label']
        self.comparison_label = widgets['comparison_label']
        
        self.materials_table = widgets['materials_table']
        self.materials_total_label = widgets['materials_total_label']
        
        self.works_table = widgets['works_table']
        self.works_total_label = widgets['works_total_label']
        
        # Создаем обработчики
        self.materials_handler = MaterialsHandler(
            self.materials_table, self.materials_total_label,
            self.deal.id, self.detail_service, self
        )
        
        self.works_handler = WorksHandler(
            self.works_table, self.works_total_label,
            self.deal.id, self.detail_service, self
        )
        
        self.products_handler = ProductsHandler(
            self.products_table, self.products_total_label, self.comparison_label,
            self.materials_table, self.works_table,
            self.deal.id, self.detail_service, self
        )
        
        # Подключаем сигналы
        self.materials_table.itemChanged.connect(self.materials_handler.on_item_changed)
        self.works_table.itemChanged.connect(self.works_handler.on_item_changed)
        self.products_table.itemChanged.connect(self.products_handler.on_item_changed)
        
        widgets['add_material_btn'].clicked.connect(self.materials_handler.add_row)
        widgets['save_materials_btn'].clicked.connect(self.materials_handler.save)
        
        widgets['add_work_btn'].clicked.connect(self.works_handler.add_row)
        widgets['save_works_btn'].clicked.connect(self.works_handler.save)
        
        widgets['add_product_btn'].clicked.connect(self.products_handler.add_row)
        widgets['save_products_btn'].clicked.connect(self.products_handler.save)
        
        # Устанавливаем делегат для автопоиска товаров
        from modules.crm.sales_funnel.product_search_delegate import ProductSearchDelegate
        from config.settings import config
        
        product_delegate = ProductSearchDelegate(config.database, self.products_table)
        product_delegate.product_selected.connect(self.products_handler.on_product_selected_from_search)
        self.products_table.setItemDelegateForColumn(0, product_delegate)

    def _init_documents_tab(self) -> None:
        """Инициализация вкладки 'Документы закупки'."""
        widgets = DocumentsTabBuilder.build_documents_tab(self.tab_documents)
        
        # Создаем обработчик документов
        self.documents_handler = DocumentsHandler(
            widgets['phrases_container'],
            widgets['phrases_layout'],
            widgets['open_documents_btn'],
            self
        )
        
        # Подключаем сигнал кнопки
        widgets['open_documents_btn'].clicked.connect(self.documents_handler.open_documents_dialog)

    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        """Создание заголовка секции."""
        label = QLabel(text)
        apply_label_style(label, "h3")
        return label

    @staticmethod
    def _create_contacts_table() -> QTableWidget:
        """Создание таблицы контактов."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["ФИО", "Отдел", "Должность", "Телефон", "E-mail", "Роль"]
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table

    def _load_data(self) -> None:
        """Загрузка данных и заполнение вкладок."""
        self.data = self.detail_service.build_deal_card(self.deal)
        
        logger.info(f"DealDetailDialog: данные загружены для сделки {self.deal.id}")

        # Обновляем заголовок
        self._update_title_from_tender()
        
        # Заполняем summary
        self._fill_summary()
        
        # Заполняем вкладки используя наши модули
        DealDataFillers.fill_overview(self.tender_info, self.tender_link_label, self.data)
        DealDataFillers.fill_customer(self.customer_info, self.customer_contacts_table, self.data)
        DealDataFillers.fill_contractor(self.contractor_info, self.contractor_contacts_table, self.data)
        
        # #region agent log
        import json
        from datetime import datetime
        from pathlib import Path
        log_file = Path(r'c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log')
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'location': 'deal_detail_dialog.py:_load_data:before_handlers',
                'message': 'Перед вызовом load_from_db для handlers',
                'data': {
                    'has_materials_handler': self.materials_handler is not None,
                    'has_works_handler': self.works_handler is not None,
                    'has_products_handler': self.products_handler is not None
                },
                'hypothesisId': 'H3',
                'sessionId': 'debug-session'
            }) + '\n')
        # #endregion agent log
        
        # Загружаем товары/материалы/работы
        if self.materials_handler:
            self.materials_handler.load_from_db()
        if self.works_handler:
            self.works_handler.load_from_db()
        if self.products_handler:
            self.products_handler.load_from_db()
        
        # Загружаем чат
        self._load_chat()
        
        # Заполняем документы
        if self.documents_handler:
            self.documents_handler.fill_documents(self.data)

    def _update_title_from_tender(self) -> None:
        """Обновление заголовка окна по названию закупки."""
        tender = self.data.get("tender", {}) or {}
        auction_name = tender.get("auction_name") or self.deal.name
        self.setWindowTitle(f"Карточка сделки — {auction_name}")
        self.title_label.setText(f"Сделка: {auction_name}")

    def _fill_summary(self) -> None:
        """Заполнение summary-блока."""
        tender = self.data.get("tender", {}) or {}
        deal_data = self.data.get("deal", {}) or {}

        # Сумма закупки
        tender_amount = tender.get("final_price") or tender.get("initial_price")
        if tender_amount is not None:
            self.summary_amount_label.setText(f"<b>Сумма закупки:</b> {tender_amount:,.0f} ₽".replace(",", " "))
        else:
            self.summary_amount_label.setText("<b>Сумма закупки:</b> —")

        # Сумма сделки (КП)
        deal_amount = deal_data.get("amount")
        if deal_amount is not None:
            self.summary_deal_kp_label.setText(f"<b>Сумма сделки (КП):</b> {deal_amount:,.0f} ₽".replace(",", " "))
        else:
            self.summary_deal_kp_label.setText("<b>Сумма сделки (КП):</b> —")

        # Маржа
        margin = deal_data.get("margin")
        if margin is not None:
            self.summary_margin_label.setText(f"<b>Маржа:</b> {margin:.1f}%")
        else:
            self.summary_margin_label.setText("<b>Маржа:</b> —")

        # Статус
        status = deal_data.get("status") or "—"
        self.summary_status_label.setText(f"<b>Статус сделки:</b> {status}")

        # Этап воронки
        stage_name = deal_data.get("stage_name") or deal_data.get("stage_id") or "—"
        self.summary_stage_label.setText(f"<b>Этап воронки:</b> {stage_name}")

        # Реестр
        registry_type = (tender.get("registry_type") or "").upper()
        registry_text = registry_type if registry_type else "—"
        self.summary_registry_label.setText(f"<b>Реестр:</b> {registry_text}")

        # Номер закупки
        purchase_number = tender.get("purchase_number") or tender.get("id") or tender.get("tender_id")
        if purchase_number:
            self.summary_tender_number_label.setText(f"<b>Номер закупки:</b> {purchase_number}")
        else:
            self.summary_tender_number_label.setText("<b>Номер закупки:</b> —")

        # Ответственный
        owner_id = deal_data.get("user_id")
        owner_text = str(owner_id) if owner_id is not None else "—"
        self.summary_owner_label.setText(f"<b>Ответственный (user_id):</b> {owner_text}")

        # Регион
        region_name = tender.get("region_name")
        if region_name:
            self.summary_region_label.setText(f"<b>📍 Регион:</b> {region_name}")
        else:
            self.summary_region_label.setText("<b>📍 Регион:</b> —")

        # Адрес поставки
        delivery_region = tender.get("delivery_region")
        if delivery_region:
            delivery_address = tender.get("delivery_address")
            if delivery_address:
                delivery_text = f"{delivery_region}, {delivery_address}"
            else:
                delivery_text = delivery_region
            self.summary_delivery_label.setText(f"<b>🚚 Адрес поставки:</b> {delivery_text}")
        else:
            self.summary_delivery_label.setText("<b>🚚 Адрес поставки:</b> не указан")

    def _load_chat(self) -> None:
        """Загрузка виджета чата."""
        try:
            from modules.crm.sales_funnel.deal_chat_service import DealChatService
            from modules.crm.sales_funnel.deal_chat_widget import DealChatWidget

            chat_service = DealChatService(self.detail_service.db_manager)
            current_user_id = self.deal.user_id if hasattr(self.deal, "user_id") else 1

            self.chat_widget = DealChatWidget(
                deal_id=self.deal.id,
                current_user_id=current_user_id,
                chat_service=chat_service,
                detail_service=self.detail_service,
                parent=self.tab_overview,
            )

            layout = self.tab_overview.layout()
            if layout:
                layout.addWidget(self.chat_widget)
        except Exception as exc:
            logger.error(f"Ошибка при загрузке чата: {exc}", exc_info=True)
            error_label = QLabel(f"Ошибка загрузки чата: {exc}")
            apply_label_style(error_label, "normal")
            error_label.setStyleSheet(f"color: {COLORS['error']};")
            layout = self.tab_overview.layout()
            if layout:
                layout.addWidget(error_label)
    
    def _update_price_comparison(self) -> None:
        """Обновление сравнения цен (публичный метод для вызова из обработчиков)."""
        if self.products_handler:
            self.products_handler.update_price_comparison()

