"""
MODULE: modules.crm.sales_funnel.deal_detail_dialog_backup
RESPONSIBILITY: Legacy/Backup implementation of Detailed Deal Card Dialog.
ALLOWED: PyQt5, loguru, modules.crm.sales_funnel.models, modules.crm.sales_funnel.deal_detail_service.
FORBIDDEN: Logic duplication with new version (use for reference only).
ERRORS: None.

Диалоговая форма детальной карточки сделки (воронка продаж).

Основной сценарий: клик по карточке сделки в воронке "Поставка материалов".
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
    QTableWidgetItem,
    QTextEdit,
    QPushButton,
)
from PyQt5.QtCore import Qt

from loguru import logger
from modules.styles.general_styles import apply_label_style, apply_button_style, apply_input_style, COLORS
from modules.crm.sales_funnel.models import Deal
from modules.crm.sales_funnel.deal_detail_service import DealDetailService


class DealDetailDialog(QDialog):
    """Окно детальной карточки сделки."""

    def __init__(self, deal: Deal, detail_service: DealDetailService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.deal = deal
        self.detail_service = detail_service
        self.data: Dict[str, Any] = {}
        self.setWindowTitle(f"Карточка сделки — {deal.name}")
        self.resize(900, 700)
        # #region agent log
        logger.info(f"DealDetailDialog.__init__: создание диалога для сделки {deal.id}")
        # #endregion
        self._init_ui()
        # #region agent log
        logger.info(f"DealDetailDialog.__init__: _init_ui завершен, tab_documents exists={hasattr(self, 'tab_documents')}")
        # #endregion
        self._load_data()
        # #region agent log
        logger.info(f"DealDetailDialog.__init__: _load_data завершен, диалог готов")
        # #endregion

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Заголовок диалога (обновляется после загрузки данных по закупке)
        self.title_label = QLabel(f"Сделка: {self.deal.name}")
        apply_label_style(self.title_label, "h2")
        main_layout.addWidget(self.title_label)

        # --------- Summary-блок с ключевой информацией ---------
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(16)

        # Левая колонка: суммы, маржа, статус, этап воронки
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

        # Правая колонка: реестр, номер закупки, ответственный
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
        main_layout.addLayout(summary_layout)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Вкладки
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

        self._init_overview_tab()
        self._init_customer_tab()
        self._init_contractor_tab()
        self._init_items_tab()
        # #region agent log
        logger.info(f"DealDetailDialog._init_ui: перед _init_documents_tab, tab_documents exists={hasattr(self, 'tab_documents')}")
        # #endregion
        self._init_documents_tab()
        # #region agent log
        logger.info(f"DealDetailDialog._init_ui: после _init_documents_tab, tab_documents exists={hasattr(self, 'tab_documents')}")
        # #endregion

    def _init_overview_tab(self) -> None:
        layout = QVBoxLayout(self.tab_overview)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.tender_info = QTextEdit()
        self.tender_info.setReadOnly(True)
        layout.addWidget(self._make_section_label("Закупка"))
        layout.addWidget(self.tender_info)

        # Ссылка на закупку (кликабельная)
        self.tender_link_label = QLabel()
        apply_label_style(self.tender_link_label, "small")
        self.tender_link_label.setTextFormat(Qt.RichText)
        self.tender_link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.tender_link_label.setOpenExternalLinks(True)
        self.tender_link_label.hide()
        layout.addWidget(self.tender_link_label)

        # Чат вместо раздела "Сделка" (без заголовка)
        self.chat_widget = None
        # Загрузка чата происходит в _load_data после создания сервиса

    def _init_customer_tab(self) -> None:
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
        from PyQt5.QtWidgets import QSplitter, QComboBox, QStyledItemDelegate, QScrollArea
        from PyQt5.QtCore import Qt
        
        # Создаем главный контейнер с QScrollArea для всей вкладки
        self.items_scroll_area = QScrollArea(self.tab_items)
        self.items_scroll_area.setWidgetResizable(True)
        self.items_scroll_area.setFrameShape(QScrollArea.NoFrame)
        
        # Контейнер для контента (с явным parent)
        self.items_content_widget = QWidget()
        layout = QVBoxLayout(self.items_content_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Устанавливаем скролл как основной виджет вкладки
        tab_layout = QVBoxLayout(self.tab_items)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(self.items_scroll_area)

        # Раздел 0: Товары из базы данных (с автопоиском)
        products_label = self._make_section_label("🛒 Коммерческое предложение (товары из базы данных)")
        layout.addWidget(products_label)
        
        # Контейнер для таблицы и итогов
        products_container = QWidget()
        products_layout = QHBoxLayout(products_container)
        products_layout.setContentsMargins(0, 0, 0, 0)
        
        # Таблица товаров с фиксированной шириной
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(6)
        self.products_table.setHorizontalHeaderLabels(
            ["Наименование (начните вводить для поиска)", "Производитель", "Кол-во", "Ед.", "Цена за ед.", "Итого"]
        )
        self.products_table.horizontalHeader().setStretchLastSection(False)
        # Фиксируем ширину колонок
        self.products_table.setColumnWidth(0, 300)  # Наименование
        self.products_table.setColumnWidth(1, 150)  # Производитель
        self.products_table.setColumnWidth(2, 80)   # Кол-во
        self.products_table.setColumnWidth(3, 60)   # Ед.
        self.products_table.setColumnWidth(4, 100)  # Цена
        self.products_table.setColumnWidth(5, 100)  # Итого
        self.products_table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.products_table.itemChanged.connect(self._on_product_item_changed)
        
        # Устанавливаем делегат для автопоиска в колонке "Наименование"
        # Используем DatabaseConfig для product_catalog_2
        from modules.crm.sales_funnel.product_search_delegate import ProductSearchDelegate
        from config.settings import config
        
        # Передаем DatabaseConfig для product_catalog_2
        product_delegate = ProductSearchDelegate(config.database, self.products_table)
        product_delegate.product_selected.connect(self._on_product_selected_from_search)
        self.products_table.setItemDelegateForColumn(0, product_delegate)
        
        products_layout.addWidget(self.products_table, 3)
        
        # Блок итогов справа с цветовой индикацией
        products_totals = QWidget()
        products_totals.setMaximumWidth(250)
        products_totals_layout = QVBoxLayout(products_totals)
        products_totals_layout.setContentsMargins(10, 10, 10, 10)
        products_totals_layout.setSpacing(10)
        
        totals_label_products = QLabel("<b>Итоги и сравнение:</b>")
        products_totals_layout.addWidget(totals_label_products)
        
        self.products_total_label = QLabel("Итого по КП:\n0.00 руб.")
        self.products_total_label.setStyleSheet(f"font-size: 14px; color: {COLORS['primary']}; font-weight: bold;")
        products_totals_layout.addWidget(self.products_total_label)
        
        # Сравнение с материалами
        self.comparison_label = QLabel("Сравнение со сметой:\n—")
        self.comparison_label.setStyleSheet("font-size: 12px; padding: 10px; border-radius: 5px; background-color: #f0f0f0;")
        self.comparison_label.setWordWrap(True)
        products_totals_layout.addWidget(self.comparison_label)
        
        # Кнопки
        add_product_btn = QPushButton("➕ Добавить товар")
        apply_button_style(add_product_btn, "secondary")
        add_product_btn.clicked.connect(self._add_product_row)
        products_totals_layout.addWidget(add_product_btn)
        
        save_products_btn = QPushButton("💾 Сохранить КП")
        apply_button_style(save_products_btn, "primary")
        save_products_btn.clicked.connect(self._save_products)
        products_totals_layout.addWidget(save_products_btn)
        
        products_totals_layout.addStretch()
        products_layout.addWidget(products_totals, 1)
        
        layout.addWidget(products_container)

        # Раздел 1: Материалы из проектной документации (редактируемая таблица)
        materials_label = self._make_section_label("📦 Материалы из проектной документации")
        layout.addWidget(materials_label)
        
        # Контейнер для таблицы и итогов
        materials_container = QWidget()
        materials_layout = QHBoxLayout(materials_container)
        materials_layout.setContentsMargins(0, 0, 0, 0)
        
        self.materials_table = QTableWidget()
        self.materials_table.setColumnCount(5)
        self.materials_table.setHorizontalHeaderLabels(
            ["Наименование", "Кол-во", "Ед.", "Цена за ед.", "Итого"]
        )
        self.materials_table.horizontalHeader().setStretchLastSection(False)
        # Фиксируем ширину колонок (как у товаров)
        self.materials_table.setColumnWidth(0, 300)  # Наименование
        self.materials_table.setColumnWidth(1, 80)   # Кол-во
        self.materials_table.setColumnWidth(2, 60)   # Ед.
        self.materials_table.setColumnWidth(3, 100)  # Цена
        self.materials_table.setColumnWidth(4, 100)  # Итого
        self.materials_table.setEditTriggers(QTableWidget.AllEditTriggers)  # Редактируемая
        self.materials_table.itemChanged.connect(self._on_material_item_changed)
        materials_layout.addWidget(self.materials_table, 3)
        
        # Блок итогов справа
        materials_totals = QWidget()
        materials_totals.setMaximumWidth(200)
        materials_totals_layout = QVBoxLayout(materials_totals)
        materials_totals_layout.setContentsMargins(10, 10, 10, 10)
        materials_totals_layout.setSpacing(10)
        
        totals_label = QLabel("<b>Итоги:</b>")
        materials_totals_layout.addWidget(totals_label)
        
        self.materials_total_label = QLabel("Итого по материалам:\n0.00 руб.")
        self.materials_total_label.setStyleSheet(f"font-size: 14px; color: {COLORS['primary']}; font-weight: bold;")
        materials_totals_layout.addWidget(self.materials_total_label)
        
        # Кнопки
        add_material_btn = QPushButton("➕ Добавить строку")
        apply_button_style(add_material_btn, "secondary")
        add_material_btn.clicked.connect(self._add_material_row)
        materials_totals_layout.addWidget(add_material_btn)
        
        save_materials_btn = QPushButton("💾 Сохранить материалы")
        apply_button_style(save_materials_btn, "primary")
        save_materials_btn.clicked.connect(self._save_materials)
        materials_totals_layout.addWidget(save_materials_btn)
        
        materials_totals_layout.addStretch()
        materials_layout.addWidget(materials_totals, 1)
        
        layout.addWidget(materials_container)

        # Раздел 2: Работы из проектной документации (редактируемая таблица)
        works_label = self._make_section_label("🛠 Работы из проектной документации")
        layout.addWidget(works_label)
        
        # Контейнер для таблицы и итогов
        works_container = QWidget()
        works_layout = QHBoxLayout(works_container)
        works_layout.setContentsMargins(0, 0, 0, 0)
        
        self.works_table = QTableWidget()
        self.works_table.setColumnCount(5)
        self.works_table.setHorizontalHeaderLabels(
            ["Наименование", "Объем", "Ед.", "Цена за ед.", "Итого"]
        )
        self.works_table.horizontalHeader().setStretchLastSection(False)
        # Фиксируем ширину колонок (как у товаров и материалов)
        self.works_table.setColumnWidth(0, 300)  # Наименование
        self.works_table.setColumnWidth(1, 80)   # Объем
        self.works_table.setColumnWidth(2, 60)   # Ед.
        self.works_table.setColumnWidth(3, 100)  # Цена
        self.works_table.setColumnWidth(4, 100)  # Итого
        self.works_table.setEditTriggers(QTableWidget.AllEditTriggers)  # Редактируемая
        self.works_table.itemChanged.connect(self._on_work_item_changed)
        works_layout.addWidget(self.works_table, 3)
        
        # Блок итогов справа
        works_totals = QWidget()
        works_totals.setMaximumWidth(200)
        works_totals_layout = QVBoxLayout(works_totals)
        works_totals_layout.setContentsMargins(10, 10, 10, 10)
        works_totals_layout.setSpacing(10)
        
        works_totals_label = QLabel("<b>Итоги:</b>")
        works_totals_layout.addWidget(works_totals_label)
        
        self.works_total_label = QLabel("Итого по работам:\n0.00 руб.")
        self.works_total_label.setStyleSheet(f"font-size: 14px; color: {COLORS['primary']}; font-weight: bold;")
        works_totals_layout.addWidget(self.works_total_label)
        
        # Кнопки
        add_work_btn = QPushButton("➕ Добавить строку")
        apply_button_style(add_work_btn, "secondary")
        add_work_btn.clicked.connect(self._add_work_row)
        works_totals_layout.addWidget(add_work_btn)
        
        save_works_btn = QPushButton("💾 Сохранить работы")
        apply_button_style(save_works_btn, "primary")
        save_works_btn.clicked.connect(self._save_works)
        works_totals_layout.addWidget(save_works_btn)
        
        works_totals_layout.addStretch()
        works_layout.addWidget(works_totals, 1)
        
        layout.addWidget(works_container)
        
        # Флаги для предотвращения рекурсивных вызовов при программном изменении
        self._updating_materials = False
        self._updating_works = False
        self._updating_products = False
        
        # Добавляем растяжку в конец layout
        layout.addStretch()
        
        # Устанавливаем items_content_widget в QScrollArea
        self.items_scroll_area.setWidget(self.items_content_widget)
        
        # #region agent log
        logger.info(f"DealDetailDialog._init_items_tab: таблицы товаров, материалов и работ созданы")
        # #endregion


    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        label = QLabel(text)
        apply_label_style(label, "h3")
        return label

    @staticmethod
    def _create_contacts_table() -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["ФИО", "Отдел", "Должность", "Телефон", "E-mail", "Роль"]
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table

    def _load_data(self) -> None:
        """Загружаем и раскладываем данные по вкладкам."""
        self.data = self.detail_service.build_deal_card(self.deal)
        # #region agent log
        import json
        from pathlib import Path
        log_path = Path(r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log")
        tender_data = self.data.get("tender", {}) or {}
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "detail-dialog", "hypothesisId": "H1", "location": "deal_detail_dialog.py:_load_data", "message": "Data loaded", "data": {"has_tender": bool(tender_data), "tender_keys": list(tender_data.keys())[:20] if tender_data else [], "has_customer": "customer" in tender_data, "has_delivery_dates": "delivery_start_date" in tender_data}, "timestamp": __import__('time').time_ns() // 1000000}) + "\n")
        # #endregion

        # Обновляем заголовок на основе названия закупки (auction_name)
        self._update_title_from_tender()
        self._fill_summary()
        self._fill_overview()
        self._fill_customer()
        self._fill_contractor()
        self._fill_items()
        self._load_chat()
        self._fill_documents()

    def _update_title_from_tender(self) -> None:
        """Обновляет заголовок окна/карточки по названию закупки (auction_name)."""
        tender = self.data.get("tender", {}) or {}
        auction_name = tender.get("auction_name") or self.deal.name
        self.setWindowTitle(f"Карточка сделки — {auction_name}")
        self.title_label.setText(f"Сделка: {auction_name}")

    def _fill_summary(self) -> None:
        """Заполнение верхнего summary-блока ключевой информацией."""
        tender = self.data.get("tender", {}) or {}
        deal_data = self.data.get("deal", {}) or {}

        # Сумма закупки (из реестра)
        tender_amount = tender.get("final_price") or tender.get("initial_price")
        if tender_amount is not None:
            self.summary_amount_label.setText(
                f"<b>Сумма закупки:</b> {tender_amount:,.0f} ₽".replace(",", " ")
            )
        else:
            self.summary_amount_label.setText("<b>Сумма закупки:</b> —")

        # Сумма сделки (КП / коммерческое предложение)
        deal_amount = deal_data.get("amount")
        if deal_amount is not None:
            self.summary_deal_kp_label.setText(
                f"<b>Сумма сделки (КП):</b> {deal_amount:,.0f} ₽".replace(",", " ")
            )
        else:
            self.summary_deal_kp_label.setText("<b>Сумма сделки (КП):</b> —")

        # Маржа
        margin = deal_data.get("margin")
        if margin is not None:
            self.summary_margin_label.setText(f"<b>Маржа:</b> {margin:.1f}%")
        else:
            self.summary_margin_label.setText("<b>Маржа:</b> —")

        # Статус сделки
        status = deal_data.get("status") or "—"
        self.summary_status_label.setText(f"<b>Статус сделки:</b> {status}")

        # Этап воронки (человеко-читаемое название, если есть)
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

        # Регион закупки
        region_name = tender.get("region_name")
        if region_name:
            self.summary_region_label.setText(f"<b>📍 Регион:</b> {region_name}")
        else:
            self.summary_region_label.setText("<b>📍 Регион:</b> —")

        # Адрес поставки (delivery_region)
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

    def _fill_overview(self) -> None:
        tender = self.data.get("tender", {}) or {}
        # #region agent log
        import json
        from pathlib import Path
        log_path = Path(r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "detail-dialog", "hypothesisId": "H4", "location": "deal_detail_dialog.py:_fill_overview:start", "message": "_fill_overview called", "data": {"tender_is_empty": not bool(tender), "tender_keys": list(tender.keys())[:30] if tender else [], "customer_value": tender.get("customer"), "delivery_start_date": tender.get("delivery_start_date"), "delivery_end_date": tender.get("delivery_end_date")}, "timestamp": __import__('time').time_ns() // 1000000}) + "\n")
        # #endregion

        tender_lines = []
        
        # Номер закупки
        if tender.get("purchase_number"):
            tender_lines.append(f"📄 Номер закупки: {tender['purchase_number']}")
        
        # Название закупки
        if tender.get("auction_name"):
            tender_lines.append(f"📝 Название закупки: {tender['auction_name']}")
        
        # Заказчик (балансодержатель) - текстовое поле customer из реестра контрактов
        customer_balance_holder = tender.get("customer")
        
        # Организатор торгов - данные из таблицы customer по customer_id
        customer_organizer = self.data.get("customer", {}) or {}
        organizer_name = customer_organizer.get("customer_full_name") or customer_organizer.get("customer_short_name")
        
        # #region agent log
        import json
        from pathlib import Path
        log_path = Path(r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "detail-dialog", "hypothesisId": "CUSTOMER_CHECK", "location": "deal_detail_dialog.py:_fill_overview:customer_check", "message": "Checking customer sources", "data": {"customer_from_registry_field": customer_balance_holder, "customer_id_from_registry": tender.get("customer_id"), "customer_table_object_keys": list(customer_organizer.keys()) if customer_organizer else [], "customer_full_name_from_table": customer_organizer.get("customer_full_name"), "customer_short_name_from_table": customer_organizer.get("customer_short_name"), "organizer_name_selected": organizer_name}, "timestamp": __import__('time').time_ns() // 1000000}) + "\n")
        # #endregion
        
        if customer_balance_holder:
            tender_lines.append(f"🏢 Заказчик (балансодержатель): {customer_balance_holder}")
        
        if organizer_name:
            # Показываем организатора торгов только если он отличается от балансодержателя
            if organizer_name != customer_balance_holder:
                tender_lines.append(f"📋 Организатор торгов: {organizer_name}")
            # Если балансодержатель не указан, показываем организатора как основного
            elif not customer_balance_holder:
                tender_lines.append(f"🏢 Организатор торгов: {organizer_name}")
        
        # Подрядчик
        if tender.get("contractor_full_name"):
            tender_lines.append(f"🏗 Подрядчик: {tender['contractor_full_name']}")
        
        # ОКПД
        if tender.get("okpd_name"):
            okpd_code = tender.get('okpd_main_code', '')
            if okpd_code:
                tender_lines.append(f"🧾 ОКПД: {okpd_code} {tender['okpd_name']}")
            else:
                tender_lines.append(f"🧾 ОКПД: {tender['okpd_name']}")
        
        # Сумма закупки
        if tender.get("final_price") or tender.get("initial_price"):
            price = tender.get("final_price") or tender.get("initial_price")
            tender_lines.append(f"💰 Сумма закупки: {price:,.0f} ₽".replace(",", " "))
        
        # Площадка
        if tender.get("platform_name"):
            tender_lines.append(f"🛒 Площадка: {tender['platform_name']}")
        
        # Даты из reestr_contract_44_fz
        if tender.get("start_date"):
            tender_lines.append(f"📅 Дата начала торгов: {tender['start_date']}")
        if tender.get("end_date"):
            tender_lines.append(f"📅 Дата окончания подачи заявок: {tender['end_date']}")
        if tender.get("delivery_start_date"):
            tender_lines.append(f"🚚 Начало поставки: {tender['delivery_start_date']}")
        if tender.get("delivery_end_date"):
            tender_lines.append(f"🚚 Окончание поставки: {tender['delivery_end_date']}")

        # #region agent log
        import json
        from pathlib import Path
        log_path = Path(r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "detail-dialog", "hypothesisId": "H5", "location": "deal_detail_dialog.py:_fill_overview:end", "message": "Setting tender_info text", "data": {"lines_count": len(tender_lines), "lines_preview": tender_lines[:5], "widget_visible": self.tender_info.isVisible()}, "timestamp": __import__('time').time_ns() // 1000000}) + "\n")
        # #endregion

        self.tender_info.setPlainText("\n".join(tender_lines))

        # Кликабельная ссылка на закупку
        tender_link = tender.get("tender_link")
        if tender_link:
            self.tender_link_label.setText(
                f'<a href="{tender_link}">🔗 Открыть закупку на площадке</a>'
            )
            self.tender_link_label.show()
        else:
            self.tender_link_label.hide()

    def _fill_customer(self) -> None:
        customer = self.data.get("customer") or {}
        if customer:
            lines = [
                f"ID: {customer.get('id')}",
                f"Полное название: {customer.get('customer_full_name')}",
                f"Краткое название: {customer.get('customer_short_name')}",
                f"ИНН: {customer.get('customer_inn')}",
                f"КПП: {customer.get('customer_kpp')}",
                f"Юр. адрес: {customer.get('customer_legal_address')}",
                f"Факт. адрес: {customer.get('customer_actual_address')}",
                f"Телефон: {customer.get('contact_phone')}",
                f"E-mail: {customer.get('contact_email')}",
            ]
            self.customer_info.setPlainText("\n".join(filter(None, lines)))

        contacts = (self.data.get("contacts") or {}).get("customer") or []
        self._fill_contacts_table(self.customer_contacts_table, contacts)

    def _fill_contractor(self) -> None:
        contractor = self.data.get("contractor") or {}
        if contractor:
            lines = [
                f"ID: {contractor.get('id')}",
                f"Полное название: {contractor.get('full_name')}",
                f"Краткое название: {contractor.get('short_name')}",
                f"ИНН: {contractor.get('inn')}",
                f"КПП: {contractor.get('kpp')}",
                f"Юр. адрес: {contractor.get('legal_address')}",
                f"Телефон: {contractor.get('phone')}",
                f"E-mail: {contractor.get('email')}",
            ]
            self.contractor_info.setPlainText("\n".join(filter(None, lines)))

        contacts = (self.data.get("contacts") or {}).get("contractor") or []
        self._fill_contacts_table(self.contractor_contacts_table, contacts)

    @staticmethod
    def _fill_contacts_table(table: QTableWidget, contacts: list[dict[str, Any]]) -> None:
        table.setRowCount(len(contacts))
        for row_idx, contact in enumerate(contacts):
            table.setItem(row_idx, 0, QTableWidgetItem(str(contact.get("full_name", ""))))
            table.setItem(row_idx, 1, QTableWidgetItem(str(contact.get("department", ""))))
            table.setItem(row_idx, 2, QTableWidgetItem(str(contact.get("position", ""))))
            table.setItem(row_idx, 3, QTableWidgetItem(str(contact.get("phone_mobile", ""))))
            table.setItem(row_idx, 4, QTableWidgetItem(str(contact.get("email", ""))))
            role = contact.get("role") or ""
            if contact.get("is_primary"):
                role = f"{role} (основной)".strip()
            table.setItem(row_idx, 5, QTableWidgetItem(role))

    def _fill_items(self) -> None:
        """Заполнение вкладки КП / Товары."""
        from modules.crm.sales_funnel.deal_item_repository import DealItemRepository
        
        # #region agent log
        logger.info(f"DealDetailDialog._fill_items: начало заполнения")
        # #endregion
        
        # Загружаем товары, материалы и работы из БД
        repo = DealItemRepository(self.detail_service.db_manager)
        products_kp = repo.get_items_by_deal(self.deal.id, "товар_кп")
        materials = repo.get_items_by_deal(self.deal.id, "материал")
        works = repo.get_items_by_deal(self.deal.id, "работа")
        
        # #region agent log
        logger.info(f"DealDetailDialog._fill_items: загружено products={len(products_kp)}, materials={len(materials)}, works={len(works)}")
        # #endregion
        
        # Заполняем таблицу товаров КП
        self._updating_products = True
        self.products_table.setRowCount(0)
        for product in products_kp:
            row = self.products_table.rowCount()
            self.products_table.insertRow(row)
            
            # Разбираем название (может содержать производителя в скобках)
            product_name = product.get("product_name", "")
            manufacturer = ""
            if "(" in product_name and ")" in product_name:
                parts = product_name.rsplit("(", 1)
                product_name = parts[0].strip()
                manufacturer = parts[1].replace(")", "").strip()
            
            self.products_table.setItem(row, 0, QTableWidgetItem(product_name))
            self.products_table.setItem(row, 1, QTableWidgetItem(manufacturer))
            self.products_table.setItem(row, 2, QTableWidgetItem(str(product.get("quantity", ""))))
            self.products_table.setItem(row, 3, QTableWidgetItem(str(product.get("unit", "шт"))))
            self.products_table.setItem(row, 4, QTableWidgetItem(str(product.get("price_per_unit", ""))))
            
            # Вычисляем итого
            try:
                qty = float(product.get("quantity", 0))
                price = float(product.get("price_per_unit", 0))
                total = qty * price
                self.products_table.setItem(row, 5, QTableWidgetItem(f"{total:.2f}"))
            except:
                self.products_table.setItem(row, 5, QTableWidgetItem("0.00"))
        
        # Если нет товаров, добавляем пустую строку
        if not products_kp:
            self._add_product_row()
        
        self._updating_products = False
        self._update_products_total()
        
        # Заполняем таблицу материалов
        self._updating_materials = True
        self.materials_table.setRowCount(0)  # Очищаем
        for material in materials:
            row = self.materials_table.rowCount()
            self.materials_table.insertRow(row)
            
            self.materials_table.setItem(row, 0, QTableWidgetItem(str(material.get("product_name", ""))))
            self.materials_table.setItem(row, 1, QTableWidgetItem(str(material.get("quantity", ""))))
            self.materials_table.setItem(row, 2, QTableWidgetItem(str(material.get("unit", "шт"))))
            self.materials_table.setItem(row, 3, QTableWidgetItem(str(material.get("price_per_unit", ""))))
            
            # Вычисляем итого
            try:
                qty = float(material.get("quantity", 0))
                price = float(material.get("price_per_unit", 0))
                total = qty * price
                self.materials_table.setItem(row, 4, QTableWidgetItem(f"{total:.2f}"))
            except:
                self.materials_table.setItem(row, 4, QTableWidgetItem("0.00"))
        
        # Если нет материалов, добавляем пустую строку
        if not materials:
            self._add_material_row()
        
        self._updating_materials = False
        self._update_materials_total()
        
        # Заполняем таблицу работ
        self._updating_works = True
        self.works_table.setRowCount(0)  # Очищаем
        for work in works:
            row = self.works_table.rowCount()
            self.works_table.insertRow(row)
            
            self.works_table.setItem(row, 0, QTableWidgetItem(str(work.get("product_name", ""))))
            self.works_table.setItem(row, 1, QTableWidgetItem(str(work.get("quantity", ""))))
            self.works_table.setItem(row, 2, QTableWidgetItem(str(work.get("unit", "шт"))))
            self.works_table.setItem(row, 3, QTableWidgetItem(str(work.get("price_per_unit", ""))))
            
            # Вычисляем итого
            try:
                qty = float(work.get("quantity", 0))
                price = float(work.get("price_per_unit", 0))
                total = qty * price
                self.works_table.setItem(row, 4, QTableWidgetItem(f"{total:.2f}"))
            except:
                self.works_table.setItem(row, 4, QTableWidgetItem("0.00"))
        
        # Если нет работ, добавляем пустую строку
        if not works:
            self._add_work_row()
        
        self._updating_works = False
        self._update_works_total()
        
        # Обновляем сравнение цен
        self._update_price_comparison()
        
        # #region agent log
        logger.info(f"DealDetailDialog._fill_items: завершено, products={len(products_kp)}, materials={len(materials)}, works={len(works)}")
        # #endregion

    def _load_chat(self) -> None:
        """Загрузка виджета чата в раздел 'Общая информация' вместо раздела 'Сделка'."""
        try:
            from modules.crm.sales_funnel.deal_chat_service import DealChatService
            from modules.crm.sales_funnel.deal_chat_widget import DealChatWidget

            # Создаем сервис чата
            chat_service = DealChatService(self.detail_service.db_manager)

            # Получаем текущего пользователя из deal
            current_user_id = self.deal.user_id if hasattr(self.deal, "user_id") else 1

            # Создаем виджет чата
            self.chat_widget = DealChatWidget(
                deal_id=self.deal.id,
                current_user_id=current_user_id,
                chat_service=chat_service,
                detail_service=self.detail_service,
                parent=self.tab_overview,
            )

            # Добавляем виджет в layout вкладки "Общая информация"
            layout = self.tab_overview.layout()
            if layout:
                layout.addWidget(self.chat_widget)
        except Exception as exc:
            logger.error(f"Ошибка при загрузке чата: {exc}", exc_info=True)
            # В случае ошибки показываем сообщение
            error_label = QLabel(f"Ошибка загрузки чата: {exc}")
            apply_label_style(error_label, "normal")
            error_label.setStyleSheet(f"color: {COLORS['error']};")
            layout = self.tab_overview.layout()
            if layout:
                layout.addWidget(error_label)

    def _init_documents_tab(self) -> None:
        """Инициализация вкладки 'Документы закупки'."""
        from PyQt5.QtWidgets import QScrollArea, QFrame
        # #region agent log
        logger.info(f"DealDetailDialog._init_documents_tab: начало, tab_documents exists={hasattr(self, 'tab_documents')}")
        if not hasattr(self, 'tab_documents'):
            logger.error("DealDetailDialog._init_documents_tab: tab_documents не существует!")
            return
        # #endregion
        layout = QVBoxLayout(self.tab_documents)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Раздел: Найденные фразы в документации (карточки)
        phrases_label = self._make_section_label("📋 Найденные фразы в документации")
        layout.addWidget(phrases_label)
        
        # Скролл-область для фраз
        phrases_scroll = QScrollArea()
        phrases_scroll.setWidgetResizable(True)
        phrases_scroll.setStyleSheet(f"background-color: {COLORS['white']}; border: 1px solid {COLORS['border']};")
        
        self.phrases_container = QWidget()
        self.phrases_layout = QVBoxLayout(self.phrases_container)
        self.phrases_layout.setContentsMargins(5, 5, 5, 5)
        self.phrases_layout.setSpacing(5)
        
        phrases_scroll.setWidget(self.phrases_container)
        layout.addWidget(phrases_scroll)

        # Раздел: Документы закупки (кнопка для открытия списка)
        layout.addStretch()
        
        documents_label = self._make_section_label("📄 Документы закупки")
        layout.addWidget(documents_label)
        
        # Кнопка для открытия диалога с документами
        self.open_documents_btn = QPushButton("📄 Открыть документы закупки")
        apply_button_style(self.open_documents_btn, "primary")
        self.open_documents_btn.setFixedHeight(50)
        self.open_documents_btn.clicked.connect(self._open_documents_dialog_from_button)
        layout.addWidget(self.open_documents_btn)
        
        # #region agent log
        logger.info(f"DealDetailDialog._init_documents_tab: завершено, layout создан")
        # #endregion

    def _fill_documents(self) -> None:
        """Заполнение вкладки 'Документы закупки' найденными фразами и ссылками."""
        from PyQt5.QtWidgets import QFrame
        from PyQt5.QtCore import Qt, QSize
        import os
        
        # #region agent log
        logger.info(f"DealDetailDialog._fill_documents: начало, tab_documents exists={hasattr(self, 'tab_documents')}")
        if not hasattr(self, 'tab_documents'):
            logger.error("DealDetailDialog._fill_documents: tab_documents не существует!")
            return
        # #endregion
        
        # Получаем найденные фразы из данных estimate_items (они содержат данные из tender_document_match_details)
        estimate_items = self.data.get("estimate_items", [])
        document_links_data = self.data.get("document_links", [])
        
        # #region agent log
        logger.info(f"DealDetailDialog._fill_documents: estimate_items count={len(estimate_items)}, document_links count={len(document_links_data)}")
        # #endregion
        
        # Очищаем предыдущие фразы
        while self.phrases_layout.count():
            item = self.phrases_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Заполняем найденные фразы (карточки)
        for item in estimate_items:
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
            
            # Создаем карточку для фразы
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
            
            # Найденный текст (что конкретно найдено)
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
            
            # Точность с цветом
            score_label = QLabel(f"Точность: {score:.1f}%")
            score_label.setStyleSheet(f"color: {text_color}; font-weight: bold; font-size: 12px;")
            card_layout.addWidget(score_label)
            
            self.phrases_layout.addWidget(phrase_card)
        
        # Если нет фраз
        if not estimate_items:
            no_phrases_label = QLabel("Найденные фразы отсутствуют")
            no_phrases_label.setStyleSheet(f"color: {COLORS['text_light']}; padding: 10px;")
            self.phrases_layout.addWidget(no_phrases_label)
        
        # Сохраняем ссылки на документы для открытия в диалоге
        self.document_links = []
        for doc_link in document_links_data:
            doc_url = doc_link.get("document_links", "")
            file_name = doc_link.get("file_name", "Документ")
            self.document_links.append({"url": doc_url, "name": file_name})
        
        # Обновляем текст кнопки с количеством документов
        if hasattr(self, 'open_documents_btn'):
            doc_count = len(self.document_links)
            if doc_count > 0:
                self.open_documents_btn.setText(f"📄 Открыть документы закупки ({doc_count})")
                self.open_documents_btn.setEnabled(True)
            else:
                self.open_documents_btn.setText("📄 Документы отсутствуют")
                self.open_documents_btn.setEnabled(False)
        
        # #region agent log
        logger.info(f"DealDetailDialog._fill_documents: завершено, phrases={len(estimate_items)}, documents={len(document_links_data)}")
        # #endregion
    
    def _open_documents_dialog_from_button(self) -> None:
        """Открытие диалога со списком документов для скачивания (вызов из кнопки)."""
        if not self.document_links:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Информация", "Документы отсутствуют")
            return
        
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Документы закупки")
        dialog.resize(700, 500)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Заголовок
        title_label = QLabel(f"<h3>📄 Документы закупки ({len(self.document_links)} файлов)</h3>")
        layout.addWidget(title_label)
        
        # Создаем таблицу вместо списка для лучшего отображения
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
            download_btn.clicked.connect(lambda checked, url=doc['url'], name=doc['name']: self._download_document(url, name))
            docs_table.setCellWidget(idx, 1, download_btn)
        
        layout.addWidget(docs_table)
        
        # Кнопки внизу
        buttons_layout = QHBoxLayout()
        
        download_all_btn = QPushButton("⬇ Скачать все")
        apply_button_style(download_all_btn, "primary")
        download_all_btn.clicked.connect(lambda: self._download_all_documents())
        buttons_layout.addWidget(download_all_btn)
        
        close_btn = QPushButton("Закрыть")
        apply_button_style(close_btn, "secondary")
        close_btn.clicked.connect(dialog.close)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
        dialog.exec_()
    def _download_document(self, url: str, file_name: str) -> None:
        """Скачивание одного документа."""
        try:
            import urllib.request
            import os
            from PyQt5.QtWidgets import QFileDialog, QMessageBox
            
            # Предлагаем пользователю выбрать место сохранения
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить документ",
                file_name,
                "Все файлы (*.*)"
            )
            
            if save_path:
                logger.info(f"Скачивание документа: {url} -> {save_path}")
                urllib.request.urlretrieve(url, save_path)
                QMessageBox.information(self, "Успех", f"Документ '{file_name}' успешно скачан!")
        except Exception as exc:
            logger.error(f"Ошибка при скачивании документа {file_name}: {exc}", exc_info=True)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", f"Не удалось скачать документ '{file_name}': {exc}")
    
    def _download_all_documents(self) -> None:
        """Скачивание всех документов."""
        try:
            if not hasattr(self, 'document_links') or not self.document_links:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Предупреждение", "Нет документов для скачивания")
                return
            
            import os
            from PyQt5.QtWidgets import QFileDialog, QMessageBox
            
            # Предлагаем пользователю выбрать папку для сохранения
            save_dir = QFileDialog.getExistingDirectory(
                self,
                "Выберите папку для сохранения документов"
            )
            
            if save_dir:
                import urllib.request
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
                
                QMessageBox.information(self, "Результат скачивания", msg)
        except Exception as exc:
            logger.error(f"Ошибка при скачивании всех документов: {exc}", exc_info=True)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", f"Не удалось скачать документы: {exc}")
    
    def _add_material_row(self) -> None:
        """Добавление новой строки в таблицу материалов."""
        row_count = self.materials_table.rowCount()
        self.materials_table.insertRow(row_count)
        # Устанавливаем значения по умолчанию
        self.materials_table.setItem(row_count, 1, QTableWidgetItem("1"))  # Кол-во
        self.materials_table.setItem(row_count, 2, QTableWidgetItem("шт"))  # Ед.
        self.materials_table.setItem(row_count, 3, QTableWidgetItem("0"))  # Цена
        self.materials_table.setItem(row_count, 4, QTableWidgetItem("0.00"))  # Итого
    
    def _add_work_row(self) -> None:
        """Добавление новой строки в таблицу работ."""
        row_count = self.works_table.rowCount()
        self.works_table.insertRow(row_count)
        # Устанавливаем значения по умолчанию
        self.works_table.setItem(row_count, 1, QTableWidgetItem("1"))  # Объем
        self.works_table.setItem(row_count, 2, QTableWidgetItem("шт"))  # Ед.
        self.works_table.setItem(row_count, 3, QTableWidgetItem("0"))  # Цена
        self.works_table.setItem(row_count, 4, QTableWidgetItem("0.00"))  # Итого
    
    def _on_material_item_changed(self, item: QTableWidgetItem) -> None:
        """Обработка изменения ячейки в таблице материалов."""
        if self._updating_materials:
            return
        
        row = item.row()
        col = item.column()
        
        # Пересчитываем итого для строки, если изменились Кол-во или Цена
        if col in (1, 3):  # Кол-во или Цена
            self._recalculate_material_row(row)
        
        # Обновляем общий итог
        self._update_materials_total()
    
    def _on_work_item_changed(self, item: QTableWidgetItem) -> None:
        """Обработка изменения ячейки в таблице работ."""
        if self._updating_works:
            return
        
        row = item.row()
        col = item.column()
        
        # Пересчитываем итого для строки, если изменились Объем или Цена
        if col in (1, 3):  # Объем или Цена
            self._recalculate_work_row(row)
        
        # Обновляем общий итог
        self._update_works_total()
    
    def _recalculate_material_row(self, row: int) -> None:
        """Пересчет итого для строки материалов."""
        try:
            self._updating_materials = True
            
            quantity_item = self.materials_table.item(row, 1)
            price_item = self.materials_table.item(row, 3)
            
            if not quantity_item or not price_item:
                return
            
            try:
                quantity = float(quantity_item.text() or "0")
                price = float(price_item.text() or "0")
                total = quantity * price
                
                total_item = self.materials_table.item(row, 4)
                if not total_item:
                    total_item = QTableWidgetItem()
                    self.materials_table.setItem(row, 4, total_item)
                
                total_item.setText(f"{total:.2f}")
            except ValueError:
                pass
        finally:
            self._updating_materials = False
    
    def _recalculate_work_row(self, row: int) -> None:
        """Пересчет итого для строки работ."""
        try:
            self._updating_works = True
            
            quantity_item = self.works_table.item(row, 1)
            price_item = self.works_table.item(row, 3)
            
            if not quantity_item or not price_item:
                return
            
            try:
                quantity = float(quantity_item.text() or "0")
                price = float(price_item.text() or "0")
                total = quantity * price
                
                total_item = self.works_table.item(row, 4)
                if not total_item:
                    total_item = QTableWidgetItem()
                    self.works_table.setItem(row, 4, total_item)
                
                total_item.setText(f"{total:.2f}")
            except ValueError:
                pass
        finally:
            self._updating_works = False
    
    def _update_materials_total(self) -> None:
        """Обновление общего итога по материалам."""
        total = 0.0
        for row in range(self.materials_table.rowCount()):
            total_item = self.materials_table.item(row, 4)
            if total_item:
                try:
                    total += float(total_item.text() or "0")
                except ValueError:
                    pass
        
        self.materials_total_label.setText(f"Итого по материалам:\n{total:,.2f} руб.")
    
    def _update_works_total(self) -> None:
        """Обновление общего итога по работам."""
        total = 0.0
        for row in range(self.works_table.rowCount()):
            total_item = self.works_table.item(row, 4)
            if total_item:
                try:
                    total += float(total_item.text() or "0")
                except ValueError:
                    pass
        
        self.works_total_label.setText(f"Итого по работам:\n{total:,.2f} руб.")
    
    def _save_materials(self) -> None:
        """Сохранение материалов в БД."""
        from PyQt5.QtWidgets import QMessageBox
        from modules.crm.sales_funnel.deal_item_repository import DealItemRepository
        
        try:
            # Собираем данные из таблицы
            materials = []
            for row in range(self.materials_table.rowCount()):
                name_item = self.materials_table.item(row, 0)
                qty_item = self.materials_table.item(row, 1)
                unit_item = self.materials_table.item(row, 2)
                price_item = self.materials_table.item(row, 3)
                
                if not name_item or not name_item.text().strip():
                    continue  # Пропускаем пустые строки
                
                materials.append({
                    "product_name": name_item.text().strip(),
                    "quantity": float(qty_item.text() or "0") if qty_item else 0,
                    "unit": unit_item.text().strip() if unit_item else "шт",
                    "price_per_unit": float(price_item.text() or "0") if price_item else 0,
                })
            
            # Сохраняем в БД
            repo = DealItemRepository(self.detail_service.db_manager)
            success = repo.save_items(self.deal.id, materials, "материал")
            
            if success:
                QMessageBox.information(self, "Успех", f"Сохранено {len(materials)} материалов")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить материалы")
        except Exception as exc:
            logger.error(f"Ошибка при сохранении материалов: {exc}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить материалы: {exc}")
    
    def _save_works(self) -> None:
        """Сохранение работ в БД."""
        from PyQt5.QtWidgets import QMessageBox
        from modules.crm.sales_funnel.deal_item_repository import DealItemRepository
        
        try:
            # Собираем данные из таблицы
            works = []
            for row in range(self.works_table.rowCount()):
                name_item = self.works_table.item(row, 0)
                qty_item = self.works_table.item(row, 1)
                unit_item = self.works_table.item(row, 2)
                price_item = self.works_table.item(row, 3)
                
                if not name_item or not name_item.text().strip():
                    continue  # Пропускаем пустые строки
                
                works.append({
                    "product_name": name_item.text().strip(),
                    "quantity": float(qty_item.text() or "0") if qty_item else 0,
                    "unit": unit_item.text().strip() if unit_item else "шт",
                    "price_per_unit": float(price_item.text() or "0") if price_item else 0,
                })
            
            # Сохраняем в БД
            repo = DealItemRepository(self.detail_service.db_manager)
            success = repo.save_items(self.deal.id, works, "работа")
            
            if success:
                QMessageBox.information(self, "Успех", f"Сохранено {len(works)} работ")
                self._update_price_comparison()  # Обновляем сравнение цен
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить работы")
        except Exception as exc:
            logger.error(f"Ошибка при сохранении работ: {exc}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить работы: {exc}")
    
    def _add_product_row(self) -> None:
        """Добавление новой строки в таблицу товаров из БД."""
        row_count = self.products_table.rowCount()
        self.products_table.insertRow(row_count)
        # Значения по умолчанию
        self.products_table.setItem(row_count, 2, QTableWidgetItem("1"))  # Кол-во
        self.products_table.setItem(row_count, 3, QTableWidgetItem("шт"))  # Ед.
        self.products_table.setItem(row_count, 4, QTableWidgetItem("0"))  # Цена
        self.products_table.setItem(row_count, 5, QTableWidgetItem("0.00"))  # Итого
    
    def _on_product_item_changed(self, item: QTableWidgetItem) -> None:
        """Обработка изменения ячейки в таблице товаров."""
        if self._updating_products:
            return
        
        row = item.row()
        col = item.column()
        
        # Пересчитываем итого для строки, если изменились Кол-во или Цена
        if col in (2, 4):  # Кол-во или Цена
            self._recalculate_product_row(row)
        
        # Обновляем общий итог и сравнение
        self._update_products_total()
        self._update_price_comparison()
    
    def _recalculate_product_row(self, row: int) -> None:
        """Пересчет итого для строки товаров."""
        try:
            self._updating_products = True
            
            quantity_item = self.products_table.item(row, 2)
            price_item = self.products_table.item(row, 4)
            
            if not quantity_item or not price_item:
                return
            
            try:
                quantity = float(quantity_item.text() or "0")
                price = float(price_item.text() or "0")
                total = quantity * price
                
                total_item = self.products_table.item(row, 5)
                if not total_item:
                    total_item = QTableWidgetItem()
                    self.products_table.setItem(row, 5, total_item)
                
                total_item.setText(f"{total:.2f}")
            except ValueError:
                pass
        finally:
            self._updating_products = False
    
    def _update_products_total(self) -> None:
        """Обновление общего итога по товарам из БД."""
        total = 0.0
        for row in range(self.products_table.rowCount()):
            total_item = self.products_table.item(row, 5)
            if total_item:
                try:
                    total += float(total_item.text() or "0")
                except ValueError:
                    pass
        
        self.products_total_label.setText(f"Итого по КП:\n{total:,.2f} руб.")
    
    def _update_price_comparison(self) -> None:
        """Обновление сравнения цен КП со сметой."""
        try:
            # Считаем итого по КП (товары из БД)
            kp_total = 0.0
            for row in range(self.products_table.rowCount()):
                total_item = self.products_table.item(row, 5)
                if total_item:
                    try:
                        kp_total += float(total_item.text() or "0")
                    except ValueError:
                        pass
            
            # Считаем итого по смете (материалы + работы)
            estimate_total = 0.0
            
            # Материалы
            for row in range(self.materials_table.rowCount()):
                total_item = self.materials_table.item(row, 4)
                if total_item:
                    try:
                        estimate_total += float(total_item.text() or "0")
                    except ValueError:
                        pass
            
            # Работы
            for row in range(self.works_table.rowCount()):
                total_item = self.works_table.item(row, 4)
                if total_item:
                    try:
                        estimate_total += float(total_item.text() or "0")
                    except ValueError:
                        pass
            
            # Сравниваем
            if estimate_total == 0:
                self.comparison_label.setText("Сравнение со сметой:\n—\n(Заполните материалы и работы)")
                self.comparison_label.setStyleSheet("font-size: 12px; padding: 10px; border-radius: 5px; background-color: #f0f0f0;")
                return
            
            difference = kp_total - estimate_total
            percent_diff = (difference / estimate_total) * 100 if estimate_total > 0 else 0
            
            # Цветовая индикация
            if kp_total < estimate_total * 0.9:  # КП дешевле сметы на 10% и больше
                color = "#4CAF50"  # Зеленый - отлично
                icon = "🟢"
                verdict = "ВЫГОДНО!"
            elif kp_total < estimate_total:  # КП дешевле сметы, но меньше 10%
                color = "#8BC34A"  # Светло-зеленый - хорошо
                icon = "🟢"
                verdict = "Выгодно"
            elif kp_total <= estimate_total * 1.1:  # КП дороже, но не более 10%
                color = "#FFC107"  # Желтый - приемлемо
                icon = "🟡"
                verdict = "Приемлемо"
            elif kp_total <= estimate_total * 1.3:  # КП дороже на 10-30%
                color = "#FF9800"  # Оранжевый - дорого
                icon = "🟠"
                verdict = "Дорого"
            else:  # КП дороже на 30% и более
                color = "#F44336"  # Красный - очень дорого
                icon = "🔴"
                verdict = "ОЧЕНЬ ДОРОГО"
            
            text = f"{icon} {verdict}\n"
            text += f"КП: {kp_total:,.2f} руб.\n"
            text += f"Смета: {estimate_total:,.2f} руб.\n"
            text += f"Разница: {difference:+,.2f} руб. ({percent_diff:+.1f}%)"
            
            self.comparison_label.setText(text)
            self.comparison_label.setStyleSheet(f"font-size: 12px; padding: 10px; border-radius: 5px; background-color: {color}; color: white; font-weight: bold;")
        except Exception as exc:
            logger.error(f"Ошибка при сравнении цен: {exc}", exc_info=True)
    
    def _on_product_selected_from_search(self, row: int, product_data: dict) -> None:
        """Обработка выбора товара из автопоиска."""
        try:
            self._updating_products = True
            
            # Заполняем ячейки данными товара
            self.products_table.setItem(row, 0, QTableWidgetItem(product_data.get("name", "")))
            self.products_table.setItem(row, 1, QTableWidgetItem(product_data.get("manufacturer", "")))
            self.products_table.setItem(row, 3, QTableWidgetItem(product_data.get("unit", "шт")))
            self.products_table.setItem(row, 4, QTableWidgetItem(str(product_data.get("price", 0))))
            
            # Пересчитываем итого
            qty_item = self.products_table.item(row, 2)
            if not qty_item:
                qty_item = QTableWidgetItem("1")
                self.products_table.setItem(row, 2, qty_item)
            
            self._recalculate_product_row(row)
            self._update_products_total()
            self._update_price_comparison()
        finally:
            self._updating_products = False
    
    def _save_products(self) -> None:
        """Сохранение товаров КП в БД."""
        from PyQt5.QtWidgets import QMessageBox
        from modules.crm.sales_funnel.deal_item_repository import DealItemRepository
        
        try:
            # Собираем данные из таблицы
            products = []
            for row in range(self.products_table.rowCount()):
                name_item = self.products_table.item(row, 0)
                manufacturer_item = self.products_table.item(row, 1)
                qty_item = self.products_table.item(row, 2)
                unit_item = self.products_table.item(row, 3)
                price_item = self.products_table.item(row, 4)
                
                if not name_item or not name_item.text().strip():
                    continue  # Пропускаем пустые строки
                
                product_name = name_item.text().strip()
                if manufacturer_item and manufacturer_item.text().strip():
                    product_name += f" ({manufacturer_item.text().strip()})"
                
                products.append({
                    "product_name": product_name,
                    "quantity": float(qty_item.text() or "0") if qty_item else 0,
                    "unit": unit_item.text().strip() if unit_item else "шт",
                    "price_per_unit": float(price_item.text() or "0") if price_item else 0,
                })
            
            # Сохраняем в БД
            repo = DealItemRepository(self.detail_service.db_manager)
            success = repo.save_items(self.deal.id, products, "товар_кп")
            
            if success:
                QMessageBox.information(self, "Успех", f"Сохранено {len(products)} товаров в КП")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить товары КП")
        except Exception as exc:
            logger.error(f"Ошибка при сохранении товаров КП: {exc}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить товары КП: {exc}")


