"""
Построитель UI для виджета коммерческих предложений

Отвечает за создание и настройку пользовательского интерфейса KPWidget.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTabWidget, QSpinBox, QFrame, QHeaderView,
    QScrollArea, QDoubleSpinBox, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt

from modules.styles.general_styles import (
    apply_button_style, apply_input_style, apply_label_style,
    apply_combobox_style, apply_frame_style, SIZES,
    apply_text_style_light_italic, apply_scroll_area_style,
    apply_text_color, apply_font_weight, apply_separator_style
)
from modules.styles.kp_styles import (
    apply_kp_widget_theme, apply_kp_info_frame_style,
    apply_kp_total_frame_style
)
from modules.kp.logic import calculate_working_days, format_date_for_display


@dataclass
class KPUIControls:
    """Контейнер для всех UI элементов виджета КП"""
    # Вкладки
    tabs: QTabWidget
    
    # Фильтры
    search_field: QLineEdit
    category_combo: QComboBox
    subcategory_combo: QComboBox
    manufacturer_combo: QComboBox
    
    # Таблица товаров
    product_table: QTableWidget
    
    # Добавление в корзину
    quantity_type_combo: QComboBox
    quantity_input: QSpinBox
    weight_input: QDoubleSpinBox
    calculated_quantity_label: QLabel
    btn_add: QPushButton
    
    # Информация о корзине
    cart_info_label: QLabel
    
    # Корзина
    cart_table: QTableWidget
    apply_global_discount: QComboBox
    apply_discount_btn: QPushButton
    
    # Форма КП
    object_name_input: QLineEdit
    company_name_input: QLineEdit
    contact_person_input: QLineEdit
    kp_validity_lbl: QLabel
    payment_conditions_lbl: QLabel
    delivery_term_lbl: QLabel
    shipping_conditions_combo: QComboBox
    delivery_address_frame: QFrame
    delivery_address_input: QLineEdit
    delivery_cost_input: QDoubleSpinBox
    recalculate_kp_btn: QPushButton
    total_lbl: QLabel


def _build_filters_section(
    parent: QWidget,
    on_search_changed,
    on_category_changed,
    on_subcategory_changed,
    on_filter_changed
) -> tuple[QFrame, QLineEdit, QComboBox, QComboBox, QComboBox]:
    """Построение секции фильтров и поиска"""
    filters_frame = QFrame()
    apply_frame_style(filters_frame, 'card')
    filters_layout = QVBoxLayout(filters_frame)
    
    # Поиск по названию
    search_row = QHBoxLayout()
    search_label = QLabel("Поиск по названию:")
    apply_label_style(search_label, 'normal')
    search_row.addWidget(search_label)
    
    search_field = QLineEdit()
    search_field.setPlaceholderText("Введите название товара...")
    apply_input_style(search_field)
    search_field.textChanged.connect(on_search_changed)
    search_row.addWidget(search_field)
    search_row.addStretch()
    filters_layout.addLayout(search_row)
    
    # Каскадные фильтры
    filters_row = QHBoxLayout()
    
    # Категория
    category_label = QLabel("Категория:")
    apply_label_style(category_label, 'normal')
    filters_row.addWidget(category_label)
    
    category_combo = QComboBox()
    category_combo.addItem("Все категории", None)
    apply_combobox_style(category_combo)
    category_combo.currentIndexChanged.connect(on_category_changed)
    filters_row.addWidget(category_combo)
    
    # Подкатегория
    subcategory_label = QLabel("Подкатегория:")
    apply_label_style(subcategory_label, 'normal')
    filters_row.addWidget(subcategory_label)
    
    subcategory_combo = QComboBox()
    subcategory_combo.addItem("Все подкатегории", None)
    subcategory_combo.setEnabled(False)
    apply_combobox_style(subcategory_combo)
    subcategory_combo.currentIndexChanged.connect(on_subcategory_changed)
    filters_row.addWidget(subcategory_combo)
    
    # Производитель
    manufacturer_label = QLabel("Производитель:")
    apply_label_style(manufacturer_label, 'normal')
    filters_row.addWidget(manufacturer_label)
    
    manufacturer_combo = QComboBox()
    manufacturer_combo.addItem("Все производители", None)
    apply_combobox_style(manufacturer_combo)
    manufacturer_combo.currentIndexChanged.connect(on_filter_changed)
    filters_row.addWidget(manufacturer_combo)
    
    filters_row.addStretch()
    filters_layout.addLayout(filters_row)
    
    return filters_frame, search_field, category_combo, subcategory_combo, manufacturer_combo


def _build_products_table(
    on_selection_changed,
    on_double_click
) -> QTableWidget:
    """Построение таблицы товаров"""
    product_table = QTableWidget(0, 7)
    product_table.setHorizontalHeaderLabels([
        "Наименование", "Ед. изм.", "Вес (кг)", "Цена (₽)",
        "Производитель", "Категория", "Подкатегория"
    ])
    
    COLUMN_WIDTHS = {
        1: 20,  # Ед. изм.
        2: 20,  # Вес (кг)
        3: 50,  # Цена (₽)
        4: 130,  # Производитель
        5: 130,  # Категория
    }
    
    product_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    for col, width in COLUMN_WIDTHS.items():
        product_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Interactive)
        product_table.setColumnWidth(col, width)
        product_table.horizontalHeader().setMinimumSectionSize(width)
    product_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
    
    product_table.setSelectionBehavior(QTableWidget.SelectRows)
    product_table.setSelectionMode(QTableWidget.SingleSelection)
    product_table.itemSelectionChanged.connect(on_selection_changed)
    product_table.itemDoubleClicked.connect(on_double_click)
    
    return product_table


def _build_add_to_cart_section(
    on_quantity_type_changed,
    on_quantity_changed,
    on_add_clicked
) -> tuple[QFrame, QComboBox, QSpinBox, QDoubleSpinBox, QLabel, QPushButton]:
    """Построение секции добавления товара в корзину"""
    add_frame = QFrame()
    apply_frame_style(add_frame, 'card')
    add_layout = QHBoxLayout(add_frame)
    add_layout.setSpacing(8)
    
    quantity_type_label = QLabel("Тип ввода:")
    apply_label_style(quantity_type_label, 'normal')
    add_layout.addWidget(quantity_type_label)
    
    quantity_type_combo = QComboBox()
    quantity_type_combo.addItems(["Количество (шт)", "Вес (кг)"])
    apply_combobox_style(quantity_type_combo)
    quantity_type_combo.currentIndexChanged.connect(on_quantity_type_changed)
    add_layout.addWidget(quantity_type_combo)
    
    quantity_label = QLabel("Значение:")
    apply_label_style(quantity_label, 'normal')
    add_layout.addWidget(quantity_label)
    
    quantity_input = QSpinBox()
    quantity_input.setMinimum(1)
    quantity_input.setMaximum(999999)
    quantity_input.setValue(1)
    quantity_input.valueChanged.connect(on_quantity_changed)
    apply_input_style(quantity_input)
    add_layout.addWidget(quantity_input)
    
    weight_input = QDoubleSpinBox()
    weight_input.setMinimum(0.01)
    weight_input.setMaximum(999999.99)
    weight_input.setDecimals(2)
    weight_input.setValue(1.0)
    weight_input.setVisible(False)
    weight_input.valueChanged.connect(on_quantity_changed)
    apply_input_style(weight_input)
    add_layout.addWidget(weight_input)
    
    calculated_quantity_label = QLabel("")
    apply_label_style(calculated_quantity_label, 'normal')
    apply_text_color(calculated_quantity_label, 'primary')
    apply_font_weight(calculated_quantity_label, 'bold')
    calculated_quantity_label.setContentsMargins(10, 0, 10, 0)
    add_layout.addWidget(calculated_quantity_label)
    
    btn_add = QPushButton("➕ Добавить в корзину")
    apply_button_style(btn_add, 'primary')
    btn_add.clicked.connect(on_add_clicked)
    add_layout.addWidget(btn_add)
    add_layout.addStretch()
    
    return add_frame, quantity_type_combo, quantity_input, weight_input, calculated_quantity_label, btn_add


def _build_cart_info_section(
    on_go_to_cart
) -> tuple[QFrame, QLabel]:
    """Построение секции информации о корзине"""
    cart_info_frame = QFrame()
    apply_kp_info_frame_style(cart_info_frame)
    cart_info_layout = QHBoxLayout(cart_info_frame)
    cart_info_layout.setContentsMargins(8, 4, 8, 4)
    
    cart_info_label = QLabel("В корзине: 0 товаров")
    apply_label_style(cart_info_label, 'normal')
    cart_info_layout.addWidget(cart_info_label)
    cart_info_layout.addStretch()
    
    btn_go_to_cart = QPushButton("Перейти в корзину →")
    apply_button_style(btn_go_to_cart, 'secondary')
    btn_go_to_cart.clicked.connect(on_go_to_cart)
    cart_info_layout.addWidget(btn_go_to_cart)
    
    return cart_info_frame, cart_info_label


def _build_cart_table() -> QTableWidget:
    """Построение таблицы корзины"""
    cart_table = QTableWidget(0, 8)
    cart_table.setHorizontalHeaderLabels([
        "Наименование", "Ед. изм.", "Количество", "Цена за ед. (₽)",
        "Скидка", "Цена со скидкой (₽)", "Итого (₽)", "Действия"
    ])
    cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    cart_table.setSelectionBehavior(QTableWidget.SelectRows)
    cart_table.verticalHeader().setDefaultSectionSize(SIZES['table_row_height'])
    
    min_table_height = cart_table.horizontalHeader().height() + (SIZES['table_row_height'] * 10) + 20
    cart_table.setMinimumHeight(min_table_height)
    cart_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    
    return cart_table


def _build_discount_section(
    on_apply_discount
) -> tuple[QFrame, QComboBox, QPushButton]:
    """Построение секции глобальной скидки"""
    discount_frame = QFrame()
    apply_frame_style(discount_frame, 'card')
    discount_layout = QHBoxLayout(discount_frame)
    discount_layout.setSpacing(8)
    
    discount_label = QLabel("Глобальная скидка:")
    apply_label_style(discount_label, 'normal')
    discount_layout.addWidget(discount_label)
    
    apply_global_discount = QComboBox()
    apply_global_discount.addItems(["Нет скидки", "3%", "5%", "10%", "15%", "20%"])
    apply_combobox_style(apply_global_discount)
    
    apply_discount_btn = QPushButton("Применить скидку ко всем позициям")
    apply_button_style(apply_discount_btn, 'outline')
    apply_discount_btn.clicked.connect(on_apply_discount)
    
    discount_layout.addWidget(apply_global_discount)
    discount_layout.addWidget(apply_discount_btn)
    discount_layout.addStretch()
    
    return discount_frame, apply_global_discount, apply_discount_btn


def _build_kp_form_section(
    on_shipping_changed,
    on_delivery_address_update,
    on_recalculate
) -> tuple[QFrame, QLineEdit, QLineEdit, QLineEdit, QLabel, QLabel, QLabel, QComboBox, QFrame, QLineEdit, QDoubleSpinBox, QPushButton]:
    """Построение формы коммерческого предложения"""
    kp_form_frame = QFrame()
    apply_frame_style(kp_form_frame, 'card')
    kp_form_layout = QVBoxLayout(kp_form_frame)
    kp_form_layout.setSpacing(12)
    
    # Заголовок
    form_title = QLabel("Данные коммерческого предложения")
    apply_label_style(form_title, 'h3')
    kp_form_layout.addWidget(form_title)
    
    # Сетка для полей формы
    form_grid = QGridLayout()
    form_grid.setSpacing(10)
    form_grid.setColumnStretch(1, 1)
    
    # Наименование объекта
    object_name_label = QLabel("Наименование объекта:")
    apply_label_style(object_name_label, 'normal')
    form_grid.addWidget(object_name_label, 0, 0)
    
    object_name_input = QLineEdit()
    object_name_input.setPlaceholderText("Введите наименование объекта")
    apply_input_style(object_name_input)
    form_grid.addWidget(object_name_input, 0, 1)
    
    # Наименование компании
    company_name_label = QLabel("Наименование компании:")
    apply_label_style(company_name_label, 'normal')
    form_grid.addWidget(company_name_label, 1, 0)
    
    company_name_input = QLineEdit()
    company_name_input.setPlaceholderText("Введите наименование компании")
    apply_input_style(company_name_input)
    form_grid.addWidget(company_name_input, 1, 1)
    
    # Контактное лицо
    contact_person_label = QLabel("Контактное лицо:")
    apply_label_style(contact_person_label, 'normal')
    form_grid.addWidget(contact_person_label, 2, 0)
    
    contact_person_input = QLineEdit()
    contact_person_input.setPlaceholderText("Введите контактное лицо")
    apply_input_style(contact_person_input)
    form_grid.addWidget(contact_person_input, 2, 1)
    
    kp_form_layout.addLayout(form_grid)
    
    # Разделитель
    separator = QFrame()
    separator.setFrameShape(QFrame.HLine)
    apply_separator_style(separator)
    kp_form_layout.addWidget(separator)
    
    # Условия поставки
    conditions_title = QLabel("Условия поставки")
    apply_label_style(conditions_title, 'h3')
    kp_form_layout.addWidget(conditions_title)
    
    conditions_grid = QGridLayout()
    conditions_grid.setSpacing(8)
    conditions_grid.setColumnStretch(1, 1)
    
    # Срок действия КП
    current_date = datetime.now()
    valid_until_date = calculate_working_days(current_date, 5)
    valid_until_str = format_date_for_display(valid_until_date)
    
    kp_validity_label = QLabel("Срок действия КП:")
    apply_label_style(kp_validity_label, 'normal')
    conditions_grid.addWidget(kp_validity_label, 0, 0)
    
    kp_validity_lbl = QLabel(f"Действует до {valid_until_str} (5 рабочих дней от {format_date_for_display(current_date)})")
    apply_label_style(kp_validity_lbl, 'normal')
    apply_text_style_light_italic(kp_validity_lbl)
    conditions_grid.addWidget(kp_validity_lbl, 0, 1)
    
    # Условия оплаты
    payment_conditions_label = QLabel("Условия оплаты:")
    apply_label_style(payment_conditions_label, 'normal')
    conditions_grid.addWidget(payment_conditions_label, 1, 0)
    
    payment_conditions_lbl = QLabel("Предоплата по счету 100%")
    apply_label_style(payment_conditions_lbl, 'normal')
    apply_text_style_light_italic(payment_conditions_lbl)
    conditions_grid.addWidget(payment_conditions_lbl, 1, 1)
    
    # Срок поставки
    delivery_term_label = QLabel("Срок поставки:")
    apply_label_style(delivery_term_label, 'normal')
    conditions_grid.addWidget(delivery_term_label, 2, 0)
    
    delivery_term_lbl = QLabel("5 рабочих дней")
    apply_label_style(delivery_term_lbl, 'normal')
    apply_text_style_light_italic(delivery_term_lbl)
    conditions_grid.addWidget(delivery_term_lbl, 2, 1)
    
    # Условия отгрузки
    shipping_conditions_label = QLabel("Условия отгрузки:")
    apply_label_style(shipping_conditions_label, 'normal')
    conditions_grid.addWidget(shipping_conditions_label, 3, 0)
    
    shipping_conditions_combo = QComboBox()
    shipping_conditions_combo.addItems([
        "Самовывоз со склада: МО, г. Реутов, ул. Фабричная д.12",
        "Доставка до объекта"
    ])
    apply_combobox_style(shipping_conditions_combo)
    shipping_conditions_combo.currentIndexChanged.connect(on_shipping_changed)
    conditions_grid.addWidget(shipping_conditions_combo, 3, 1)
    
    kp_form_layout.addLayout(conditions_grid)
    
    # Поля для доставки
    delivery_address_frame = QFrame()
    delivery_address_frame.setVisible(False)
    delivery_address_layout = QVBoxLayout(delivery_address_frame)
    delivery_address_layout.setSpacing(8)
    
    # Адрес доставки
    delivery_address_row = QHBoxLayout()
    delivery_address_label = QLabel("Адрес доставки:")
    apply_label_style(delivery_address_label, 'normal')
    delivery_address_row.addWidget(delivery_address_label)
    
    delivery_address_input = QLineEdit()
    delivery_address_input.setPlaceholderText("Введите адрес доставки")
    apply_input_style(delivery_address_input)
    object_name_input.textChanged.connect(on_delivery_address_update)
    delivery_address_row.addWidget(delivery_address_input)
    delivery_address_layout.addLayout(delivery_address_row)
    
    # Сумма доставки
    delivery_cost_row = QHBoxLayout()
    delivery_cost_label = QLabel("Сумма доставки (₽):")
    apply_label_style(delivery_cost_label, 'normal')
    delivery_cost_row.addWidget(delivery_cost_label)
    
    delivery_cost_input = QDoubleSpinBox()
    delivery_cost_input.setMinimum(0.0)
    delivery_cost_input.setMaximum(99999999.99)
    delivery_cost_input.setDecimals(2)
    delivery_cost_input.setValue(0.0)
    apply_input_style(delivery_cost_input)
    delivery_cost_row.addWidget(delivery_cost_input)
    
    recalculate_kp_btn = QPushButton("Пересчитать КП")
    apply_button_style(recalculate_kp_btn, 'primary')
    recalculate_kp_btn.clicked.connect(on_recalculate)
    delivery_cost_row.addWidget(recalculate_kp_btn)
    delivery_cost_row.addStretch()
    delivery_address_layout.addLayout(delivery_cost_row)
    
    kp_form_layout.addWidget(delivery_address_frame)
    
    return (
        kp_form_frame, object_name_input, company_name_input, contact_person_input,
        kp_validity_lbl, payment_conditions_lbl, delivery_term_lbl,
        shipping_conditions_combo, delivery_address_frame, delivery_address_input,
        delivery_cost_input, recalculate_kp_btn
    )


def _build_total_section() -> tuple[QFrame, QLabel]:
    """Построение секции итоговой суммы"""
    total_frame = QFrame()
    apply_kp_total_frame_style(total_frame)
    total_layout = QHBoxLayout(total_frame)
    total_layout.setContentsMargins(0, 0, 0, 0)
    total_layout.addStretch()
    
    total_lbl = QLabel("Итого с НДС: 0.00 ₽")
    apply_label_style(total_lbl, 'h2')
    apply_text_color(total_lbl, 'white')
    apply_font_weight(total_lbl, 'bold')
    total_layout.addWidget(total_lbl)
    
    return total_frame, total_lbl


def build_kp_ui(
    parent: QWidget,
    on_search_changed,
    on_category_changed,
    on_subcategory_changed,
    on_filter_changed,
    on_selection_changed,
    on_double_click,
    on_quantity_type_changed,
    on_quantity_changed,
    on_add_clicked,
    on_go_to_cart,
    on_apply_discount,
    on_shipping_changed,
    on_delivery_address_update,
    on_recalculate,
    update_cart_table_height
) -> KPUIControls:
    """
    Построение всего UI для виджета коммерческих предложений
    
    Returns:
        KPUIControls с всеми созданными виджетами
    """
    main_vbox = QVBoxLayout(parent)
    
    # Вкладки
    tabs = QTabWidget()
    main_vbox.addWidget(tabs)
    
    # === ВКЛАДКА "ОСНОВНАЯ" ===
    main_tab = QWidget()
    main_tab_vbox = QVBoxLayout(main_tab)
    
    # Фильтры и поиск
    filters_frame, search_field, category_combo, subcategory_combo, manufacturer_combo = _build_filters_section(
        parent, on_search_changed, on_category_changed, on_subcategory_changed, on_filter_changed
    )
    main_tab_vbox.addWidget(filters_frame)
    
    # Каталог товаров
    products_label = QLabel("Каталог товаров")
    apply_label_style(products_label, 'h3')
    main_tab_vbox.addWidget(products_label)
    
    # Таблица товаров
    product_table = _build_products_table(on_selection_changed, on_double_click)
    main_tab_vbox.addWidget(product_table)
    
    # Добавление в корзину
    add_frame, quantity_type_combo, quantity_input, weight_input, calculated_quantity_label, btn_add = _build_add_to_cart_section(
        on_quantity_type_changed, on_quantity_changed, on_add_clicked
    )
    main_tab_vbox.addWidget(add_frame)
    
    # Информация о корзине
    cart_info_frame, cart_info_label = _build_cart_info_section(
        lambda: tabs.setCurrentIndex(1)
    )
    main_tab_vbox.addWidget(cart_info_frame)
    
    # === ВКЛАДКА "КОРЗИНА" ===
    cart_tab_scroll = QScrollArea()
    cart_tab_scroll.setWidgetResizable(True)
    cart_tab_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    cart_tab_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    apply_scroll_area_style(cart_tab_scroll, 'subtle')
    
    cart_tab = QWidget()
    cart_tab_vbox = QVBoxLayout(cart_tab)
    cart_tab_vbox.setSpacing(10)
    cart_tab_vbox.setContentsMargins(10, 10, 10, 10)
    
    # Заголовок
    cart_title = QLabel("Корзина коммерческого предложения")
    apply_label_style(cart_title, 'h2')
    cart_tab_vbox.addWidget(cart_title)
    
    # Таблица корзины
    cart_table = _build_cart_table()
    cart_tab_vbox.addWidget(cart_table, stretch=1)
    update_cart_table_height()
    
    # Глобальная скидка
    discount_frame, apply_global_discount, apply_discount_btn = _build_discount_section(on_apply_discount)
    cart_tab_vbox.addWidget(discount_frame)
    
    # Форма КП
    kp_form_frame, object_name_input, company_name_input, contact_person_input, kp_validity_lbl, payment_conditions_lbl, delivery_term_lbl, shipping_conditions_combo, delivery_address_frame, delivery_address_input, delivery_cost_input, recalculate_kp_btn = _build_kp_form_section(
        on_shipping_changed, on_delivery_address_update, on_recalculate
    )
    cart_tab_vbox.addWidget(kp_form_frame)
    
    # Итоговая сумма
    total_frame, total_lbl = _build_total_section()
    cart_tab_vbox.addWidget(total_frame)
    
    # Устанавливаем виджет в прокручиваемую область
    cart_tab_scroll.setWidget(cart_tab)
    
    # Добавляем вкладки
    tabs.addTab(main_tab, "Основная")
    tabs.addTab(cart_tab_scroll, "Корзина")
    
    # Применяем единый стиль
    apply_kp_widget_theme(parent)
    
    return KPUIControls(
        tabs=tabs,
        search_field=search_field,
        category_combo=category_combo,
        subcategory_combo=subcategory_combo,
        manufacturer_combo=manufacturer_combo,
        product_table=product_table,
        quantity_type_combo=quantity_type_combo,
        quantity_input=quantity_input,
        weight_input=weight_input,
        calculated_quantity_label=calculated_quantity_label,
        btn_add=btn_add,
        cart_info_label=cart_info_label,
        cart_table=cart_table,
        apply_global_discount=apply_global_discount,
        apply_discount_btn=apply_discount_btn,
        object_name_input=object_name_input,
        company_name_input=company_name_input,
        contact_person_input=contact_person_input,
        kp_validity_lbl=kp_validity_lbl,
        payment_conditions_lbl=payment_conditions_lbl,
        delivery_term_lbl=delivery_term_lbl,
        shipping_conditions_combo=shipping_conditions_combo,
        delivery_address_frame=delivery_address_frame,
        delivery_address_input=delivery_address_input,
        delivery_cost_input=delivery_cost_input,
        recalculate_kp_btn=recalculate_kp_btn,
        total_lbl=total_lbl
    )

