"""
Виджет для создания и управления коммерческими предложениями

Виджет предоставляет интерфейс для:
- Поиска товаров по категориям, подкатегориям, производителям и названию
- Добавления товаров в коммерческое предложение
- Расчет количества упаковки при вводе веса
- Применения скидок и расчета итоговых сумм
- Конвертации валют (EUR -> RUB для производителя Гидрозо)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QSpinBox,
    QApplication, QFrame, QHeaderView, QMessageBox, QScrollArea, QDoubleSpinBox,
    QDialog, QDialogButtonBox, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics
from datetime import datetime
from typing import Optional, Dict, Any, List
from loguru import logger

# Импортируем единые стили
from modules.styles.general_styles import (
    apply_button_style, apply_input_style, apply_label_style,
    apply_combobox_style, apply_frame_style, COLORS, FONT_SIZES, SIZES
)
from modules.styles.table_styles import (
    get_table_button_style, get_table_cell_widget_container_style
)

# Импортируем бизнес-логику
from modules.kp.logic import (
    calculate_packaging_quantity,
    calculate_item_total,
    calculate_quotation_total,
    format_price,
    parse_weight_input,
    get_unit_display_name,
    calculate_working_days,
    format_date_for_display,
    distribute_delivery_cost
)

# Импортируем репозиторий и менеджер БД
from services.product_repository import ProductRepository
from services.fuzzy_search import fuzzy_search_products, combine_search_results
from core.database import DatabaseManager
from config.settings import config
from modules.kp.weight_edit_dialog import WeightEditDialog
from modules.kp.price_edit_dialog import PriceEditDialog
from modules.kp.name_edit_dialog import NameEditDialog
from modules.kp.unit_edit_dialog import UnitEditDialog


# Константа курса валют
EUR_TO_RUB_RATE = 100.0  # 1 EUR = 100 RUB


def format_price_with_spaces(price: float) -> str:
    """
    Форматирование цены с пробелами для разделения тысяч
    
    Args:
        price: Цена для форматирования
    
    Returns:
        Отформатированная строка цены (например: "3 433,00")
    """
    if price <= 0:
        return "-"
    
    # Разбиваем на целую и дробную части
    price_parts = f"{price:.2f}".split('.')
    integer_part = price_parts[0]
    decimal_part = price_parts[1] if len(price_parts) > 1 else "00"
    
    # Добавляем пробелы для разделения тысяч
    if len(integer_part) > 3:
        # Форматируем с пробелами каждые 3 цифры справа налево
        formatted_int = ''
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                formatted_int = ' ' + formatted_int
            formatted_int = digit + formatted_int
        integer_part = formatted_int
    
    return f"{integer_part},{decimal_part}"


def convert_price_to_rubles(price: float, manufacturer_name: str) -> float:
    """
    Конвертация цены в рубли
    
    Если производитель "Гидрозо", цена конвертируется из евро в рубли
    
    Args:
        price: Цена товара
        manufacturer_name: Название производителя
    
    Returns:
        Цена в рублях
    """
    if manufacturer_name and "гидрозо" in manufacturer_name.lower():
        return price * EUR_TO_RUB_RATE
    return price


class KPWidget(QWidget):
    """
    Виджет для создания коммерческих предложений
    
    Подключается к базе данных для получения товаров, категорий,
    подкатегорий, производителей и информации о ценах и упаковке.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Инициализация виджета
        
        Args:
            db_manager: Менеджер базы данных (опционально, создастся автоматически)
        """
        super().__init__()
        
        # Инициализация подключения к БД
        if db_manager is None:
            try:
                self.db_manager = DatabaseManager(config.database)
                self.db_manager.connect()
            except Exception as e:
                logger.error(f"Ошибка подключения к БД: {e}")
                QMessageBox.critical(
                    self, "Ошибка подключения",
                    f"Не удалось подключиться к базе данных:\n{e}"
                )
                self.db_manager = None
        else:
            self.db_manager = db_manager
        
        # Создаем репозиторий для работы с товарами
        if self.db_manager:
            self.product_repo = ProductRepository(self.db_manager)
        else:
            self.product_repo = None
        
        # Хранилище данных о выбранном товаре
        self.selected_product_data: Optional[Dict[str, Any]] = None
        
        # Список позиций в коммерческом предложении
        self.cart_items: List[Dict[str, Any]] = []
        
        self.init_ui()
        self.load_initial_data()
        self.load_all_products()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_vbox = QVBoxLayout(self)

        # ----- Вкладки -----
        self.tabs = QTabWidget()
        main_vbox.addWidget(self.tabs)

        # ----- ВКЛАДКА "ОСНОВНАЯ" -----
        main_tab = QWidget()
        main_tab_vbox = QVBoxLayout(main_tab)

        # --- Фильтры и поиск товаров ---
        filters_frame = QFrame()
        filters_frame.setStyleSheet(f"""
            background: {COLORS['white']};
            border-radius: 8px;
            padding: 12px;
            border: 1px solid {COLORS['border']};
        """)
        filters_layout = QVBoxLayout(filters_frame)

        # Первая строка: Поиск по названию
        search_row = QHBoxLayout()
        search_label = QLabel("Поиск по названию:")
        apply_label_style(search_label, 'normal')
        search_row.addWidget(search_label)

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Введите название товара...")
        apply_input_style(self.search_field)
        self.search_field.textChanged.connect(self.handle_search)
        search_row.addWidget(self.search_field)
        search_row.addStretch()
        filters_layout.addLayout(search_row)

        # Вторая строка: Каскадные фильтры
        filters_row = QHBoxLayout()

        # Категория
        category_label = QLabel("Категория:")
        apply_label_style(category_label, 'normal')
        filters_row.addWidget(category_label)

        self.category_combo = QComboBox()
        self.category_combo.addItem("Все категории", None)
        apply_combobox_style(self.category_combo)
        self.category_combo.currentIndexChanged.connect(self.handle_category_changed)
        filters_row.addWidget(self.category_combo)

        # Подкатегория
        subcategory_label = QLabel("Подкатегория:")
        apply_label_style(subcategory_label, 'normal')
        filters_row.addWidget(subcategory_label)

        self.subcategory_combo = QComboBox()
        self.subcategory_combo.addItem("Все подкатегории", None)
        self.subcategory_combo.setEnabled(False)  # Включается при выборе категории
        apply_combobox_style(self.subcategory_combo)
        self.subcategory_combo.currentIndexChanged.connect(self.handle_subcategory_changed)
        filters_row.addWidget(self.subcategory_combo)

        # Производитель
        manufacturer_label = QLabel("Производитель:")
        apply_label_style(manufacturer_label, 'normal')
        filters_row.addWidget(manufacturer_label)

        self.manufacturer_combo = QComboBox()
        self.manufacturer_combo.addItem("Все производители", None)
        apply_combobox_style(self.manufacturer_combo)
        self.manufacturer_combo.currentIndexChanged.connect(self.handle_search)
        filters_row.addWidget(self.manufacturer_combo)

        filters_row.addStretch()
        filters_layout.addLayout(filters_row)
        main_tab_vbox.addWidget(filters_frame)

        # --- Каталог товаров (на всю ширину) ---
        products_label = QLabel("Каталог товаров")
        apply_label_style(products_label, 'h3')
        main_tab_vbox.addWidget(products_label)

        # Таблица товаров (новый порядок колонок)
        self.product_table = QTableWidget(0, 7)
        self.product_table.setHorizontalHeaderLabels([
            "Наименование", "Ед. изм.", "Вес (кг)", "Цена (₽)",
            "Производитель", "Категория", "Подкатегория"
        ])
        
        # ============================================================
        # РАЗМЕРЫ СТОЛБЦОВ - ИЗМЕНИТЕ ЗДЕСЬ ПРИ НЕОБХОДИМОСТИ
        # ============================================================
        # Размеры в пикселях для столбцов (можно изменить по необходимости)
        COLUMN_WIDTHS = {
            1: 20,  # Ед. изм. - измените это значение для изменения ширины
            2: 20,   # Вес (кг) - измените это значение для изменения ширины
            3: 50,  # Цена (₽) - измените это значение для изменения ширины
            4: 130,  # Производитель - измените это значение для изменения ширины
            5: 130,  # Категория - измените это значение для изменения ширины
        }
        # ============================================================
        
        # Настройка режимов изменения размеров столбцов
        # Наименование - растягивается
        self.product_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # Наименование
        # Столбцы с фиксированными размерами
        for col, width in COLUMN_WIDTHS.items():
            self.product_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Interactive)
            self.product_table.setColumnWidth(col, width)
            self.product_table.horizontalHeader().setMinimumSectionSize(width)
        # Подкатегория - растягивается
        self.product_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)  # Подкатегория
        self.product_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.product_table.setSelectionMode(QTableWidget.SingleSelection)
        self.product_table.itemSelectionChanged.connect(self.handle_product_selection)
        # Обработчик двойного клика для редактирования веса
        self.product_table.itemDoubleClicked.connect(self.handle_cell_double_click)
        main_tab_vbox.addWidget(self.product_table)

        # Поля для ввода количества и добавления товара
        add_frame = QFrame()
        add_frame.setStyleSheet(f"""
            background: {COLORS['white']};
            border-radius: 6px;
            padding: 10px;
            border: 1px solid {COLORS['border']};
        """)
        add_layout = QHBoxLayout(add_frame)
        add_layout.setSpacing(8)

        quantity_type_label = QLabel("Тип ввода:")
        apply_label_style(quantity_type_label, 'normal')
        add_layout.addWidget(quantity_type_label)

        self.quantity_type_combo = QComboBox()
        self.quantity_type_combo.addItems(["Количество (шт)", "Вес (кг)"])
        apply_combobox_style(self.quantity_type_combo)
        self.quantity_type_combo.currentIndexChanged.connect(self.handle_quantity_type_change)
        add_layout.addWidget(self.quantity_type_combo)

        quantity_label = QLabel("Значение:")
        apply_label_style(quantity_label, 'normal')
        add_layout.addWidget(quantity_label)

        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(999999)
        self.quantity_input.setValue(1)
        self.quantity_input.valueChanged.connect(self.update_quantity_calculation)
        apply_input_style(self.quantity_input)
        add_layout.addWidget(self.quantity_input)
        
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setMinimum(0.01)
        self.weight_input.setMaximum(999999.99)
        self.weight_input.setDecimals(2)
        self.weight_input.setValue(1.0)
        self.weight_input.setVisible(False)
        self.weight_input.valueChanged.connect(self.update_quantity_calculation)
        apply_input_style(self.weight_input)
        add_layout.addWidget(self.weight_input)

        self.calculated_quantity_label = QLabel("")
        apply_label_style(self.calculated_quantity_label, 'normal')
        self.calculated_quantity_label.setStyleSheet(f"color: {COLORS['primary']}; font-weight: bold; padding: 0 10px;")
        add_layout.addWidget(self.calculated_quantity_label)

        self.btn_add = QPushButton("➕ Добавить в корзину")
        apply_button_style(self.btn_add, 'primary')
        self.btn_add.clicked.connect(self.handle_add_to_cart)
        add_layout.addWidget(self.btn_add)
        add_layout.addStretch()
        main_tab_vbox.addWidget(add_frame)

        # Информация о корзине (компактная)
        cart_info_frame = QFrame()
        cart_info_frame.setStyleSheet(f"""
            background: {COLORS['secondary']};
            border-radius: 6px;
            padding: 8px;
            border: 1px solid {COLORS['border']};
        """)
        cart_info_layout = QHBoxLayout(cart_info_frame)
        cart_info_layout.setContentsMargins(8, 4, 8, 4)
        
        self.cart_info_label = QLabel("В корзине: 0 товаров")
        apply_label_style(self.cart_info_label, 'normal')
        cart_info_layout.addWidget(self.cart_info_label)
        cart_info_layout.addStretch()
        
        btn_go_to_cart = QPushButton("Перейти в корзину →")
        apply_button_style(btn_go_to_cart, 'secondary')
        btn_go_to_cart.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        cart_info_layout.addWidget(btn_go_to_cart)
        main_tab_vbox.addWidget(cart_info_frame)

        # === ВКЛАДКА "КОРЗИНА" ===
        # Обертка с прокруткой для вкладки корзины
        cart_tab_scroll = QScrollArea()
        cart_tab_scroll.setWidgetResizable(True)
        cart_tab_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cart_tab_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        cart_tab_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: {COLORS['secondary']};
            }}
        """)
        
        cart_tab = QWidget()
        cart_tab_vbox = QVBoxLayout(cart_tab)
        cart_tab_vbox.setSpacing(10)
        cart_tab_vbox.setContentsMargins(10, 10, 10, 10)

        # Заголовок
        cart_title = QLabel("Корзина коммерческого предложения")
        apply_label_style(cart_title, 'h2')
        cart_tab_vbox.addWidget(cart_title)

        # Таблица добавленных товаров
        self.cart_table = QTableWidget(0, 8)
        self.cart_table.setHorizontalHeaderLabels([
            "Наименование", "Ед. изм.", "Количество", "Цена за ед. (₽)",
            "Скидка", "Цена со скидкой (₽)", "Итого (₽)", "Действия"
        ])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectRows)
        # Устанавливаем вертикальное выравнивание для ячеек
        self.cart_table.verticalHeader().setDefaultSectionSize(SIZES['table_row_height'])
        # Устанавливаем минимальную высоту таблицы для лучшей видимости товаров
        # Минимальная высота = высота заголовка + высота 10 строк + небольшой отступ
        min_table_height = self.cart_table.horizontalHeader().height() + (SIZES['table_row_height'] * 10) + 20
        self.cart_table.setMinimumHeight(min_table_height)
        # Таблица должна растягиваться по вертикали
        self.cart_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cart_tab_vbox.addWidget(self.cart_table, stretch=1)  # Добавляем stretch для растягивания
        
        # Инициализируем высоту таблицы
        self.update_cart_table_height()

        # Глобальная скидка
        discount_frame = QFrame()
        discount_frame.setStyleSheet(f"""
            background: {COLORS['white']};
            border-radius: 6px;
            padding: 10px;
            border: 1px solid {COLORS['border']};
        """)
        discount_layout = QHBoxLayout(discount_frame)
        discount_layout.setSpacing(8)

        discount_label = QLabel("Глобальная скидка:")
        apply_label_style(discount_label, 'normal')
        discount_layout.addWidget(discount_label)

        self.apply_global_discount = QComboBox()
        self.apply_global_discount.addItems(["Нет скидки", "3%", "5%", "10%", "15%", "20%"])
        apply_combobox_style(self.apply_global_discount)

        self.apply_discount_btn = QPushButton("Применить скидку ко всем позициям")
        apply_button_style(self.apply_discount_btn, 'outline')
        self.apply_discount_btn.clicked.connect(self.apply_discount_to_all)

        discount_layout.addWidget(self.apply_global_discount)
        discount_layout.addWidget(self.apply_discount_btn)
        discount_layout.addStretch()
        cart_tab_vbox.addWidget(discount_frame)

        # === ФОРМА ДЛЯ СОЗДАНИЯ КОММЕРЧЕСКОГО ПРЕДЛОЖЕНИЯ ===
        kp_form_frame = QFrame()
        kp_form_frame.setStyleSheet(f"""
            background: {COLORS['white']};
            border-radius: 6px;
            padding: 15px;
            border: 1px solid {COLORS['border']};
        """)
        kp_form_layout = QVBoxLayout(kp_form_frame)
        kp_form_layout.setSpacing(12)

        # Заголовок формы
        form_title = QLabel("Данные коммерческого предложения")
        apply_label_style(form_title, 'h3')
        kp_form_layout.addWidget(form_title)

        # Сетка для полей формы
        form_grid = QGridLayout()
        form_grid.setSpacing(10)
        form_grid.setColumnStretch(1, 1)  # Вторая колонка растягивается

        # Наименование объекта
        object_name_label = QLabel("Наименование объекта:")
        apply_label_style(object_name_label, 'normal')
        form_grid.addWidget(object_name_label, 0, 0)
        
        self.object_name_input = QLineEdit()
        self.object_name_input.setPlaceholderText("Введите наименование объекта")
        apply_input_style(self.object_name_input)
        form_grid.addWidget(self.object_name_input, 0, 1)

        # Наименование компании
        company_name_label = QLabel("Наименование компании:")
        apply_label_style(company_name_label, 'normal')
        form_grid.addWidget(company_name_label, 1, 0)
        
        self.company_name_input = QLineEdit()
        self.company_name_input.setPlaceholderText("Введите наименование компании")
        apply_input_style(self.company_name_input)
        form_grid.addWidget(self.company_name_input, 1, 1)

        # Контактное лицо
        contact_person_label = QLabel("Контактное лицо:")
        apply_label_style(contact_person_label, 'normal')
        form_grid.addWidget(contact_person_label, 2, 0)
        
        self.contact_person_input = QLineEdit()
        self.contact_person_input.setPlaceholderText("Введите контактное лицо")
        apply_input_style(self.contact_person_input)
        form_grid.addWidget(self.contact_person_input, 2, 1)

        kp_form_layout.addLayout(form_grid)

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"color: {COLORS['border']};")
        kp_form_layout.addWidget(separator)

        # Условия поставки
        conditions_title = QLabel("Условия поставки")
        apply_label_style(conditions_title, 'h3')
        kp_form_layout.addWidget(conditions_title)

        conditions_grid = QGridLayout()
        conditions_grid.setSpacing(8)
        conditions_grid.setColumnStretch(1, 1)

        # Срок действия КП (по умолчанию 5 рабочих дней)
        current_date = datetime.now()
        valid_until_date = calculate_working_days(current_date, 5)
        valid_until_str = format_date_for_display(valid_until_date)
        
        kp_validity_label = QLabel("Срок действия КП:")
        apply_label_style(kp_validity_label, 'normal')
        conditions_grid.addWidget(kp_validity_label, 0, 0)
        
        self.kp_validity_lbl = QLabel(f"Действует до {valid_until_str} (5 рабочих дней от {format_date_for_display(current_date)})")
        apply_label_style(self.kp_validity_lbl, 'normal')
        self.kp_validity_lbl.setStyleSheet(f"color: {COLORS['text_light']}; font-style: italic;")
        conditions_grid.addWidget(self.kp_validity_lbl, 0, 1)

        # Условия оплаты (по умолчанию)
        payment_conditions_label = QLabel("Условия оплаты:")
        apply_label_style(payment_conditions_label, 'normal')
        conditions_grid.addWidget(payment_conditions_label, 1, 0)
        
        self.payment_conditions_lbl = QLabel("Предоплата по счету 100%")
        apply_label_style(self.payment_conditions_lbl, 'normal')
        self.payment_conditions_lbl.setStyleSheet(f"color: {COLORS['text_light']}; font-style: italic;")
        conditions_grid.addWidget(self.payment_conditions_lbl, 1, 1)

        # Срок поставки (по умолчанию)
        delivery_term_label = QLabel("Срок поставки:")
        apply_label_style(delivery_term_label, 'normal')
        conditions_grid.addWidget(delivery_term_label, 2, 0)
        
        self.delivery_term_lbl = QLabel("5 рабочих дней")
        apply_label_style(self.delivery_term_lbl, 'normal')
        self.delivery_term_lbl.setStyleSheet(f"color: {COLORS['text_light']}; font-style: italic;")
        conditions_grid.addWidget(self.delivery_term_lbl, 2, 1)

        # Условия отгрузки (выпадающий список)
        shipping_conditions_label = QLabel("Условия отгрузки:")
        apply_label_style(shipping_conditions_label, 'normal')
        conditions_grid.addWidget(shipping_conditions_label, 3, 0)
        
        self.shipping_conditions_combo = QComboBox()
        self.shipping_conditions_combo.addItems([
            "Самовывоз со склада: МО, г. Реутов, ул. Фабричная д.12",
            "Доставка до объекта"
        ])
        apply_combobox_style(self.shipping_conditions_combo)
        self.shipping_conditions_combo.currentIndexChanged.connect(self.handle_shipping_conditions_changed)
        conditions_grid.addWidget(self.shipping_conditions_combo, 3, 1)

        kp_form_layout.addLayout(conditions_grid)

        # Поля для доставки до объекта (скрыты по умолчанию)
        self.delivery_address_frame = QFrame()
        self.delivery_address_frame.setVisible(False)
        delivery_address_layout = QVBoxLayout(self.delivery_address_frame)
        delivery_address_layout.setSpacing(8)

        # Адрес доставки
        delivery_address_row = QHBoxLayout()
        delivery_address_label = QLabel("Адрес доставки:")
        apply_label_style(delivery_address_label, 'normal')
        delivery_address_row.addWidget(delivery_address_label)
        
        self.delivery_address_input = QLineEdit()
        self.delivery_address_input.setPlaceholderText("Введите адрес доставки")
        apply_input_style(self.delivery_address_input)
        # Автозаполнение из наименования объекта при изменении
        self.object_name_input.textChanged.connect(self.update_delivery_address)
        delivery_address_row.addWidget(self.delivery_address_input)
        delivery_address_layout.addLayout(delivery_address_row)

        # Сумма доставки и кнопка пересчета
        delivery_cost_row = QHBoxLayout()
        delivery_cost_label = QLabel("Сумма доставки (₽):")
        apply_label_style(delivery_cost_label, 'normal')
        delivery_cost_row.addWidget(delivery_cost_label)
        
        self.delivery_cost_input = QDoubleSpinBox()
        self.delivery_cost_input.setMinimum(0.0)
        self.delivery_cost_input.setMaximum(99999999.99)
        self.delivery_cost_input.setDecimals(2)
        self.delivery_cost_input.setValue(0.0)
        apply_input_style(self.delivery_cost_input)
        delivery_cost_row.addWidget(self.delivery_cost_input)
        
        self.recalculate_kp_btn = QPushButton("Пересчитать КП")
        apply_button_style(self.recalculate_kp_btn, 'primary')
        self.recalculate_kp_btn.clicked.connect(self.handle_recalculate_kp_with_delivery)
        delivery_cost_row.addWidget(self.recalculate_kp_btn)
        delivery_cost_row.addStretch()
        delivery_address_layout.addLayout(delivery_cost_row)

        kp_form_layout.addWidget(self.delivery_address_frame)
        cart_tab_vbox.addWidget(kp_form_frame)

        # Итоговая сумма
        total_frame = QFrame()
        total_frame.setStyleSheet(f"""
            background: {COLORS['primary']};
            border-radius: 6px;
            padding: 12px 16px;
        """)
        total_layout = QHBoxLayout(total_frame)
        total_layout.setContentsMargins(0, 0, 0, 0)
        total_layout.addStretch()
        
        self.total_lbl = QLabel("Итого с НДС: 0.00 ₽")
        self.total_lbl.setStyleSheet(f"""
            color: white;
            font-size: {FONT_SIZES['h2']};
            font-weight: bold;
        """)
        total_layout.addWidget(self.total_lbl)
        cart_tab_vbox.addWidget(total_frame)

        # Устанавливаем виджет в прокручиваемую область
        cart_tab_scroll.setWidget(cart_tab)
        
        # Добавляем вкладки
        self.tabs.addTab(main_tab, "Основная")
        self.tabs.addTab(cart_tab_scroll, "Корзина")

        # Применяем единый стиль для всего виджета
        self.setStyleSheet(f"""
            QWidget {{ 
                background: {COLORS['secondary']};
                font-size: {FONT_SIZES['normal']};
            }}
            QTableWidget {{
                font-size: {FONT_SIZES['normal']};
                border-radius: 6px;
                background: {COLORS['white']};
            }}
            QTableWidget::item {{
                padding: 4px;
            }}
            QHeaderView::section {{
                background: {COLORS['primary']};
                color: white;
                font-weight: bold;
                padding: 6px;
                border: none;
                font-size: {FONT_SIZES['small']};
            }}
        """)

    def load_initial_data(self):
        """Загрузка начальных данных (категории, производители)"""
        if not self.product_repo:
            logger.warning("Репозиторий товаров не инициализирован")
            return

        try:
            # Загружаем категории
            categories = self.product_repo.get_categories()
            for cat in categories:
                self.category_combo.addItem(cat['name'], cat['id'])

            # Загружаем производителей
            manufacturers = self.product_repo.get_manufacturers()
            for man in manufacturers:
                self.manufacturer_combo.addItem(man['name'], man['id'])

            logger.info(f"Загружено {len(categories)} категорий и {len(manufacturers)} производителей")
        except Exception as e:
            logger.error(f"Ошибка при загрузке начальных данных: {e}")
            QMessageBox.warning(
                self, "Предупреждение",
                f"Не удалось загрузить некоторые данные:\n{e}"
            )

    def load_all_products(self):
        """Загрузка всех товаров при инициализации"""
        if not self.product_repo:
            return
        
        try:
            # Загружаем все товары без фильтров
            products = self.product_repo.search_products(limit=1000)
            self.display_products(products)
            logger.info(f"Загружено {len(products)} товаров при инициализации")
        except Exception as e:
            logger.error(f"Ошибка при загрузке всех товаров: {e}")

    def handle_category_changed(self):
        """Обработка изменения категории - загрузка подкатегорий"""
        category_id = self.category_combo.currentData()
        
        # Очищаем подкатегории
        self.subcategory_combo.clear()
        self.subcategory_combo.addItem("Все подкатегории", None)
        
        if category_id and self.product_repo:
            try:
                subcategories = self.product_repo.get_subcategories(category_id)
                for subcat in subcategories:
                    self.subcategory_combo.addItem(subcat['name'], subcat['id'])
                self.subcategory_combo.setEnabled(True)
            except Exception as e:
                logger.error(f"Ошибка при загрузке подкатегорий: {e}")
        else:
            self.subcategory_combo.setEnabled(False)
        
        # Обновляем поиск
        self.handle_search()

    def handle_subcategory_changed(self):
        """Обработка изменения подкатегории"""
        self.handle_search()

    def handle_search(self):
        """Обработка поиска товаров с поддержкой нечеткого поиска"""
        if not self.product_repo:
            QMessageBox.warning(self, "Ошибка", "База данных не подключена")
            return

        try:
            # Получаем параметры фильтрации
            category_id = self.category_combo.currentData()
            subcategory_id = self.subcategory_combo.currentData()
            manufacturer_id = self.manufacturer_combo.currentData()
            search_text = self.search_field.text().strip() or None

            # Сначала выполняем обычный поиск по фильтрам (без текста)
            products = self.product_repo.search_products(
                category_id=category_id,
                subcategory_id=subcategory_id,
                manufacturer_id=manufacturer_id,
                search_text=None,  # Не используем текстовый поиск в БД
                limit=1000
            )

            # Если есть текст для поиска, применяем нечеткий поиск
            if search_text and len(search_text) >= 2:  # Минимум 2 символа для fuzzy search
                # Разделяем на точный и нечеткий поиск
                exact_matches = [
                    p for p in products 
                    if search_text.lower() in p.get('name', '').lower()
                ]
                
                # Нечеткий поиск по всем товарам
                fuzzy_matches = fuzzy_search_products(
                    products,
                    search_text,
                    threshold=70,  # Порог совпадения 70%
                    limit=100
                )
                
                # Объединяем результаты: сначала точные, потом нечеткие
                products = combine_search_results(exact_matches, fuzzy_matches, limit=200)
                logger.debug(f"Точных совпадений: {len(exact_matches)}, нечетких: {len(fuzzy_matches)}")
            elif search_text:
                # Если текст слишком короткий, используем обычный поиск
                products = [
                    p for p in products 
                    if search_text.lower() in p.get('name', '').lower()
                ]

            # Отображаем товары
            self.display_products(products)
            logger.info(f"Найдено товаров: {len(products)}")
        except Exception as e:
            logger.error(f"Ошибка при поиске товаров: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при поиске товаров:\n{e}")

    def display_products(self, products: List[Dict[str, Any]]):
        """Отображение товаров в таблице с новым порядком колонок"""
        # Заполняем таблицу
        self.product_table.setRowCount(len(products))
        
        for row, product in enumerate(products):
            # Наименование (колонка 0) - добавляем tooltip, делаем редактируемым
            product_name = product.get('name', '')
            name_item = QTableWidgetItem(product_name)
            # Устанавливаем tooltip с полным наименованием
            name_item.setToolTip(product_name)
            # Делаем ячейку наименования редактируемой (можно кликнуть дважды)
            name_item.setFlags(name_item.flags() | Qt.ItemIsEditable)
            self.product_table.setItem(row, 0, name_item)
            
            # Единица измерения (колонка 1) - убираем тире, безопасная обработка None
            container_type_raw = product.get('container_type')
            size_raw = product.get('size')
            
            # Безопасно обрабатываем None и не-строковые значения
            container_type = ''
            if container_type_raw is not None:
                try:
                    container_type = str(container_type_raw).strip()
                except (AttributeError, TypeError):
                    container_type = ''
            
            size = ''
            if size_raw is not None:
                try:
                    size = str(size_raw).strip()
                except (AttributeError, TypeError):
                    size = ''
            
            # Формируем единицу измерения
            if container_type and size:
                # Убираем тире, если есть
                unit = f"{container_type} {size}".replace(' - ', ' ').replace('- ', '').strip()
            elif container_type:
                unit = container_type
            elif size:
                unit = size
            else:
                unit = "шт"
            unit_item = QTableWidgetItem(unit)
            # Делаем ячейку единицы измерения редактируемой (можно кликнуть дважды)
            unit_item.setFlags(unit_item.flags() | Qt.ItemIsEditable)
            self.product_table.setItem(row, 1, unit_item)
            
            # Вес упаковки (колонка 2) - редактируемое поле
            weight = product.get('weight', 0)
            try:
                weight_value = float(weight) if weight else 0
                weight_str = f"{weight_value:.2f}" if weight_value > 0 else "-"
            except (ValueError, TypeError):
                weight_str = str(weight) if weight else "-"
            weight_item = QTableWidgetItem(weight_str)
            # Делаем ячейку веса редактируемой (можно кликнуть дважды)
            weight_item.setFlags(weight_item.flags() | Qt.ItemIsEditable)
            self.product_table.setItem(row, 2, weight_item)
            
            # Цена (колонка 3) - форматирование с пробелами
            price_raw = product.get('price', 0)
            manufacturer_name = product.get('manufacturer_name', '')
            price_value = 0
            price_rub = 0
            try:
                price_value = float(price_raw) if price_raw else 0
                # Конвертируем в рубли если производитель Гидрозо
                price_rub = convert_price_to_rubles(price_value, manufacturer_name)
                if price_rub > 0:
                    # Форматируем с пробелами: 3 394,00
                    # Разбиваем на целую и дробную части
                    price_parts = f"{price_rub:.2f}".split('.')
                    integer_part = price_parts[0]
                    decimal_part = price_parts[1] if len(price_parts) > 1 else "00"
                    
                    # Добавляем пробелы для разделения тысяч
                    if len(integer_part) > 3:
                        # Форматируем с пробелами каждые 3 цифры справа налево
                        formatted_int = ''
                        for i, digit in enumerate(reversed(integer_part)):
                            if i > 0 and i % 3 == 0:
                                formatted_int = ' ' + formatted_int
                            formatted_int = digit + formatted_int
                        integer_part = formatted_int
                    
                    price_str = f"{integer_part},{decimal_part}"
                else:
                    price_str = "-"
            except (ValueError, TypeError):
                price_str = str(price_raw) if price_raw else "-"
            price_item = QTableWidgetItem(price_str)
            # Делаем ячейку цены редактируемой (можно кликнуть дважды)
            price_item.setFlags(price_item.flags() | Qt.ItemIsEditable)
            self.product_table.setItem(row, 3, price_item)
            
            # Производитель (колонка 4)
            manufacturer_item = QTableWidgetItem(manufacturer_name)
            self.product_table.setItem(row, 4, manufacturer_item)
            
            # Категория (колонка 5)
            category_name = product.get('category_name', '')
            category_item = QTableWidgetItem(category_name)
            self.product_table.setItem(row, 5, category_item)
            
            # Подкатегория (колонка 6)
            self.product_table.setItem(row, 6, QTableWidgetItem(product.get('subcategory_name', '')))
            
            # Сохраняем полные данные товара в item (с конвертированной ценой)
            product_data = product.copy()
            if price_value > 0:
                product_data['price'] = price_rub
            # Сохраняем pricing_id для обновления веса
            if 'pricing_id' in product:
                product_data['pricing_id'] = product['pricing_id']
            item = self.product_table.item(row, 0)
            if item:
                item.setData(Qt.UserRole, product_data)
        
        # Размеры столбцов уже установлены в init_ui(), здесь ничего не нужно делать

    def handle_product_selection(self):
        """Обработка выбора товара в таблице"""
        selected_row = self.product_table.currentRow()
        if selected_row < 0:
            self.selected_product_data = None
            return

        item = self.product_table.item(selected_row, 0)
        if item:
            self.selected_product_data = item.data(Qt.UserRole)
            self.update_quantity_calculation()

    def handle_cell_double_click(self, item: QTableWidgetItem):
        """Обработка двойного клика на ячейку таблицы"""
        row = item.row()
        column = item.column()
        
        # Редактирование наименования (колонка 0)
        if column == 0:
            self.edit_product_name(row)
        # Редактирование единицы измерения (колонка 1)
        elif column == 1:
            self.edit_product_unit(row)
        # Редактирование веса (колонка 2)
        elif column == 2:
            self.edit_product_weight(row)
        # Редактирование цены (колонка 3)
        elif column == 3:
            self.edit_product_price(row)
    
    def edit_product_name(self, row: int):
        """Редактирование наименования товара"""
        # Получаем данные товара
        name_item = self.product_table.item(row, 0)
        if not name_item:
            return
        
        product_data = name_item.data(Qt.UserRole)
        if not product_data:
            return
        
        product_id = product_data.get('id')
        current_name = name_item.text()
        
        if not product_id:
            QMessageBox.warning(
                self, "Ошибка",
                "Не удалось определить идентификатор товара для обновления наименования"
            )
            return
        
        # Открываем диалог редактирования
        dialog = NameEditDialog(current_name, self)
        if dialog.exec_() == QDialog.Accepted:
            new_name = dialog.get_name()
            
            # Обновляем наименование в базе данных
            if self.product_repo and self.product_repo.update_product_name(product_id, new_name):
                # Обновляем отображение в таблице
                name_item.setText(new_name)
                name_item.setToolTip(new_name)
                
                # Обновляем данные в product_data
                product_data['name'] = new_name
                name_item.setData(Qt.UserRole, product_data)
                
                # Если это выбранный товар, обновляем данные
                if self.selected_product_data == product_data:
                    self.selected_product_data = product_data
                
                QMessageBox.information(
                    self, "Успешно",
                    f"Наименование товара обновлено: {new_name}"
                )
                
                # Обновляем каталог для отображения актуальных данных
                self.handle_search()
            else:
                QMessageBox.critical(
                    self, "Ошибка",
                    "Не удалось обновить наименование товара в базе данных"
                )

    def edit_product_unit(self, row: int):
        """Редактирование единицы измерения товара"""
        # Получаем данные товара
        name_item = self.product_table.item(row, 0)
        if not name_item:
            return
        
        product_data = name_item.data(Qt.UserRole)
        if not product_data:
            return
        
        product_name = product_data.get('name', 'Товар')
        pricing_id = product_data.get('pricing_id')
        current_container_type = product_data.get('container_type', '')
        current_size = product_data.get('size', '')
        
        if not pricing_id:
            QMessageBox.warning(
                self, "Ошибка",
                "Не удалось определить идентификатор цены товара для обновления единицы измерения"
            )
            return
        
        # Открываем диалог редактирования
        dialog = UnitEditDialog(
            current_container_type or '',
            current_size or '',
            product_name,
            self
        )
        if dialog.exec_() == QDialog.Accepted:
            new_container_type = dialog.get_container_type()
            new_size = dialog.get_size()
            
            # Обновляем единицу измерения в базе данных
            if self.product_repo and self.product_repo.update_product_unit(
                pricing_id, new_container_type, new_size
            ):
                # Формируем новую единицу измерения для отображения
                if new_container_type and new_size:
                    unit = f"{new_container_type} {new_size}".replace(' - ', ' ').replace('- ', '').strip()
                elif new_container_type:
                    unit = new_container_type
                elif new_size:
                    unit = new_size
                else:
                    unit = "шт"
                
                # Обновляем отображение в таблице
                unit_item = self.product_table.item(row, 1)
                if unit_item:
                    unit_item.setText(unit)
                
                # Обновляем данные в product_data
                product_data['container_type'] = new_container_type
                product_data['size'] = new_size
                name_item.setData(Qt.UserRole, product_data)
                
                # Если это выбранный товар, обновляем расчет
                if self.selected_product_data == product_data:
                    self.selected_product_data = product_data
                    self.update_quantity_calculation()
                
                QMessageBox.information(
                    self, "Успешно",
                    f"Единица измерения обновлена: {unit}"
                )
                
                # Обновляем каталог для отображения актуальных данных
                self.handle_search()
            else:
                QMessageBox.critical(
                    self, "Ошибка",
                    "Не удалось обновить единицу измерения товара в базе данных"
                )

    def edit_product_weight(self, row: int):
        """Редактирование веса товара"""
        # Получаем данные товара
        name_item = self.product_table.item(row, 0)
        if not name_item:
            return
        
        product_data = name_item.data(Qt.UserRole)
        if not product_data:
            return
        
        product_name = product_data.get('name', 'Товар')
        pricing_id = product_data.get('pricing_id')
        
        if not pricing_id:
            QMessageBox.warning(
                self, "Ошибка",
                "Не удалось определить идентификатор цены товара для обновления веса"
            )
            return
        
        # Получаем текущий вес
        weight_item = self.product_table.item(row, 2)
        current_weight_str = weight_item.text() if weight_item else "0"
        try:
            current_weight = float(current_weight_str.replace(',', '.')) if current_weight_str != "-" else 0.0
        except ValueError:
            current_weight = 0.0
        
        # Открываем диалог редактирования
        dialog = WeightEditDialog(current_weight, product_name, self)
        if dialog.exec_() == QDialog.Accepted:
            new_weight = dialog.get_weight()
            
            # Обновляем вес в базе данных
            if self.product_repo and self.product_repo.update_product_weight(pricing_id, new_weight):
                # Обновляем отображение в таблице
                weight_item.setText(f"{new_weight:.2f}")
                
                # Обновляем данные в product_data
                product_data['weight'] = new_weight
                name_item.setData(Qt.UserRole, product_data)
                
                # Если это выбранный товар, обновляем расчет
                if self.selected_product_data == product_data:
                    self.update_quantity_calculation()
                
                QMessageBox.information(
                    self, "Успешно",
                    f"Вес товара обновлен: {new_weight:.2f} кг"
                )
                
                # Обновляем каталог для отображения актуальных данных
                self.handle_search()
            else:
                QMessageBox.critical(
                    self, "Ошибка",
                    "Не удалось обновить вес товара в базе данных"
                )

    def edit_product_price(self, row: int):
        """Редактирование цены товара"""
        # Получаем данные товара
        name_item = self.product_table.item(row, 0)
        if not name_item:
            return
        
        product_data = name_item.data(Qt.UserRole)
        if not product_data:
            return
        
        product_name = product_data.get('name', 'Товар')
        pricing_id = product_data.get('pricing_id')
        
        if not pricing_id:
            QMessageBox.warning(
                self, "Ошибка",
                "Не удалось определить идентификатор цены товара для обновления цены"
            )
            return
        
        # Получаем текущую цену
        price_item = self.product_table.item(row, 3)
        current_price_str = price_item.text() if price_item else "0"
        try:
            # Убираем пробелы и заменяем запятую на точку
            current_price_str = current_price_str.replace(' ', '').replace(',', '.')
            current_price = float(current_price_str) if current_price_str != "-" else 0.0
        except ValueError:
            current_price = 0.0
        
        # Открываем диалог редактирования
        dialog = PriceEditDialog(current_price, product_name, self)
        if dialog.exec_() == QDialog.Accepted:
            new_price = dialog.get_price()
            
            # Обновляем цену в базе данных
            if self.product_repo and self.product_repo.update_product_price(pricing_id, new_price):
                # Форматируем новую цену для отображения
                price_parts = f"{new_price:.2f}".split('.')
                integer_part = price_parts[0]
                decimal_part = price_parts[1] if len(price_parts) > 1 else "00"
                
                # Добавляем пробелы для разделения тысяч
                if len(integer_part) > 3:
                    formatted_int = ''
                    for i, digit in enumerate(reversed(integer_part)):
                        if i > 0 and i % 3 == 0:
                            formatted_int = ' ' + formatted_int
                        formatted_int = digit + formatted_int
                    integer_part = formatted_int
                
                price_str = f"{integer_part},{decimal_part}"
                
                # Обновляем отображение в таблице
                price_item.setText(price_str)
                
                # Обновляем данные в product_data
                product_data['price'] = new_price
                name_item.setData(Qt.UserRole, product_data)
                
                # Если это выбранный товар, обновляем расчет
                if self.selected_product_data == product_data:
                    self.update_quantity_calculation()
                
                QMessageBox.information(
                    self, "Успешно",
                    f"Цена товара обновлена: {price_str} ₽"
                )
                
                # Обновляем каталог для отображения актуальных данных
                self.handle_search()
            else:
                QMessageBox.critical(
                    self, "Ошибка",
                    "Не удалось обновить цену товара в базе данных"
                )

    def handle_quantity_type_change(self):
        """Обработка изменения типа ввода количества"""
        # Если выбран "Вес (кг)", показываем поле для веса
        is_weight = self.quantity_type_combo.currentIndex() == 1
        self.quantity_input.setVisible(not is_weight)
        self.weight_input.setVisible(is_weight)
        self.update_quantity_calculation()

    def update_quantity_calculation(self):
        """Обновление расчета количества упаковки"""
        if not self.selected_product_data:
            self.calculated_quantity_label.setText("")
            return

        is_weight_input = self.quantity_type_combo.currentIndex() == 1  # "Вес (кг)"
        weight_raw = self.selected_product_data.get('weight', 0)
        
        # Преобразуем weight в число
        try:
            weight = float(weight_raw) if weight_raw else 0
        except (ValueError, TypeError):
            weight = 0

        if is_weight_input and weight > 0:
            input_value = self.weight_input.value()
            calculated_qty = calculate_packaging_quantity(input_value, weight)
            unit_name = get_unit_display_name(
                self.selected_product_data.get('container_type', ''),
                self.selected_product_data.get('size', '')
            )
            self.calculated_quantity_label.setText(f"→ {calculated_qty} {unit_name}")
        else:
            self.calculated_quantity_label.setText("")

    def handle_add_to_cart(self):
        """Добавление товара в коммерческое предложение"""
        if not self.selected_product_data:
            QMessageBox.warning(self, "Предупреждение", "Выберите товар из таблицы")
            return

        try:
            # Определяем количество
            is_weight_input = self.quantity_type_combo.currentIndex() == 1
            input_value = self.weight_input.value() if is_weight_input else self.quantity_input.value()
            weight_raw = self.selected_product_data.get('weight', 0)
            
            # Преобразуем weight в число
            try:
                weight = float(weight_raw) if weight_raw else 0
            except (ValueError, TypeError):
                weight = 0

            if is_weight_input and weight > 0:
                # Рассчитываем количество упаковки
                quantity = calculate_packaging_quantity(input_value, weight)
            else:
                # Используем введенное количество
                quantity = input_value

            if quantity <= 0:
                QMessageBox.warning(self, "Предупреждение", "Количество должно быть больше нуля")
                return

            # Получаем цену (уже конвертированную в рубли)
            price_raw = self.selected_product_data.get('price', 0)
            try:
                price = float(price_raw) if price_raw else 0
            except (ValueError, TypeError):
                price = 0
            
            if price <= 0:
                QMessageBox.warning(self, "Предупреждение", "Цена товара не указана")
                return

            # Добавляем товар в корзину
            self.add_item_to_cart_table(self.selected_product_data, quantity, price)
            
            # Обновляем информацию о корзине
            self.update_cart_info()

            logger.info(f"Добавлен товар: {self.selected_product_data.get('name')}, количество: {quantity}")
        except Exception as e:
            logger.error(f"Ошибка при добавлении товара: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при добавлении товара:\n{e}")

    def add_item_to_cart_table(self, product_data: Dict[str, Any], quantity: int, price: float):
        """Добавление товара в таблицу коммерческого предложения"""
        row = self.cart_table.rowCount()
        self.cart_table.insertRow(row)

        # Наименование
        name_item = QTableWidgetItem(product_data.get('name', ''))
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self.cart_table.setItem(row, 0, name_item)

        # Единица измерения
        unit = get_unit_display_name(
            product_data.get('container_type', ''),
            product_data.get('size', '')
        )
        unit_item = QTableWidgetItem(unit)
        unit_item.setFlags(unit_item.flags() & ~Qt.ItemIsEditable)
        self.cart_table.setItem(row, 1, unit_item)

        # Количество (редактируемое через SpinBox)
        qty_spin = QSpinBox()
        qty_spin.setMinimum(1)
        qty_spin.setMaximum(999999)
        qty_spin.setValue(quantity)
        qty_spin.valueChanged.connect(lambda: self.update_cart_item_total(row))
        self.cart_table.setCellWidget(row, 2, qty_spin)

        # Цена за единицу
        price_item = QTableWidgetItem(format_price_with_spaces(price))
        price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
        price_item.setData(Qt.UserRole, price)  # Сохраняем исходную цену
        self.cart_table.setItem(row, 3, price_item)

        # Скидка (редактируемое через ComboBox)
        discount_combo = QComboBox()
        discount_combo.addItems(["0%", "3%", "5%", "10%", "15%", "20%"])
        discount_combo.currentIndexChanged.connect(lambda: self.update_cart_item_total(row))
        self.cart_table.setCellWidget(row, 4, discount_combo)

        # Цена со скидкой
        price_disc_item = QTableWidgetItem(format_price_with_spaces(price))
        price_disc_item.setFlags(price_disc_item.flags() & ~Qt.ItemIsEditable)
        self.cart_table.setItem(row, 5, price_disc_item)

        # Итого
        total_item = QTableWidgetItem(format_price_with_spaces(price * quantity))
        total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
        self.cart_table.setItem(row, 6, total_item)

        # Обновляем высоту таблицы после добавления товара
        self.update_cart_table_height()

        # Кнопка удалить (в контейнере для правильного выравнивания)
        btn_remove = QPushButton("Удалить")
        # Применяем специальный стиль для кнопок в таблицах (из отдельного модуля стилей)
        btn_remove.setStyleSheet(get_table_button_style())
        # Сохраняем row в замыкании для корректного удаления
        btn_remove.clicked.connect(lambda checked, r=row: self.remove_cart_item(r))
        
        # Создаем контейнер с выравниванием по центру (горизонтально и вертикально)
        button_container = QWidget()
        # Используем QVBoxLayout для вертикального выравнивания
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)  # Убираем все отступы
        button_layout.setSpacing(0)
        button_layout.addWidget(btn_remove)
        button_layout.setAlignment(Qt.AlignCenter)
        
        # Устанавливаем стили для контейнера (из отдельного модуля стилей)
        button_container.setStyleSheet(get_table_cell_widget_container_style())
        # Получаем высоту строки таблицы
        row_height = self.cart_table.verticalHeader().defaultSectionSize()
        if row_height <= 0:
            row_height = SIZES['table_row_height']
        # Устанавливаем фиксированную высоту контейнера равной высоте строки
        button_container.setFixedHeight(row_height)
        
        self.cart_table.setCellWidget(row, 7, button_container)
        

        # Сохраняем данные товара
        cart_item_data = {
            'product_data': product_data,
            'quantity': quantity,
            'price': price,
            'discount': 0
        }
        name_item.setData(Qt.UserRole, cart_item_data)

        self.update_total()

    def remove_cart_item(self, row: int):
        """Удаление позиции из коммерческого предложения"""
        # Находим кнопку, которая вызвала удаление
        sender = self.sender()
        if sender:
            # Находим строку, в которой находится кнопка
            for r in range(self.cart_table.rowCount()):
                widget = self.cart_table.cellWidget(r, 7)
                if widget:
                    # Проверяем, является ли sender кнопкой внутри контейнера
                    if isinstance(widget, QWidget):
                        # Ищем кнопку внутри контейнера
                        button = widget.findChild(QPushButton)
                        if button == sender:
                            self.cart_table.removeRow(r)
                            self.update_total()
                            self.update_cart_info()
                            self.update_cart_table_height()  # Обновляем высоту таблицы
                            return
        # Если не нашли, удаляем по переданному индексу
        if 0 <= row < self.cart_table.rowCount():
            self.cart_table.removeRow(row)
            self.update_total()
            self.update_cart_info()
            self.update_cart_table_height()  # Обновляем высоту таблицы

    def update_cart_item_total(self, row: int):
        """Обновление итоговой суммы по позиции"""
        try:
            # Получаем количество из SpinBox
            qty_widget = self.cart_table.cellWidget(row, 2)
            if not qty_widget:
                return
            quantity = qty_widget.value()

            # Получаем цену
            price_item = self.cart_table.item(row, 3)
            if not price_item:
                return
            price = price_item.data(Qt.UserRole) or 0

            # Получаем скидку из ComboBox
            discount_widget = self.cart_table.cellWidget(row, 4)
            if not discount_widget:
                return
            discount_str = discount_widget.currentText().replace("%", "").strip()
            try:
                discount = float(discount_str)
            except ValueError:
                discount = 0

            # Рассчитываем итоги
            total = calculate_item_total(price, quantity, discount)
            price_disc = price * (1 - discount / 100)

            # Обновляем отображение
            price_disc_item = self.cart_table.item(row, 5)
            if price_disc_item:
                price_disc_item.setText(format_price_with_spaces(price_disc))

            total_item = self.cart_table.item(row, 6)
            if total_item:
                total_item.setText(format_price_with_spaces(total))

            self.update_total()
        except Exception as e:
            logger.error(f"Ошибка при обновлении позиции: {e}")

    def update_total(self):
        """Обновление итоговой суммы коммерческого предложения"""
        total = 0.0
        for row in range(self.cart_table.rowCount()):
            total_item = self.cart_table.item(row, 6)
            if total_item:
                try:
                    # Убираем пробелы и заменяем запятую на точку для парсинга
                    val_str = total_item.text().replace(' ', '').replace(',', '.')
                    val = float(val_str)
                    total += val
                except ValueError:
                    continue
        # Форматируем итоговую сумму с пробелами
        total_formatted = format_price_with_spaces(total)
        self.total_lbl.setText(f"Итого с НДС: {total_formatted} ₽")
    
    def update_cart_info(self):
        """Обновление информации о количестве товаров в корзине"""
        count = self.cart_table.rowCount()
        self.cart_info_label.setText(f"В корзине: {count} {'товар' if count == 1 else 'товаров' if count < 5 else 'товаров'}")
    
    def update_cart_table_height(self):
        """
        Динамическое обновление высоты таблицы корзины в зависимости от количества товаров
        
        Таблица будет иметь минимальную высоту для отображения всех товаров,
        но не будет превышать максимальную высоту для удобства просмотра.
        """
        row_count = self.cart_table.rowCount()
        
        # Если товаров нет, используем минимальную высоту
        if row_count == 0:
            min_height = self.cart_table.horizontalHeader().height() + 50
        else:
            # Высота = заголовок + высота всех строк + небольшой отступ
            # Минимум 5 строк для видимости, максимум 20 строк для удобства
            visible_rows = min(max(row_count, 5), 20)
            min_height = (
                self.cart_table.horizontalHeader().height() + 
                (SIZES['table_row_height'] * visible_rows) + 
                20
            )
        
        self.cart_table.setMinimumHeight(min_height)

    def apply_discount_to_all(self):
        """Применение глобальной скидки ко всем позициям"""
        disc_txt = self.apply_global_discount.currentText()
        
        for row in range(self.cart_table.rowCount()):
            discount_widget = self.cart_table.cellWidget(row, 4)
            if discount_widget:
                # Устанавливаем значение в ComboBox
                index = discount_widget.findText(disc_txt)
                if index >= 0:
                    discount_widget.setCurrentIndex(index)
                else:
                    discount_widget.setCurrentIndex(0)  # "0%" по умолчанию
                self.update_cart_item_total(row)

    def handle_shipping_conditions_changed(self):
        """Обработка изменения условий отгрузки"""
        is_delivery = self.shipping_conditions_combo.currentIndex() == 1  # "Доставка до объекта"
        self.delivery_address_frame.setVisible(is_delivery)
        
        # Если выбрана доставка, обновляем адрес из наименования объекта
        if is_delivery:
            self.update_delivery_address()

    def update_delivery_address(self):
        """Обновление адреса доставки из наименования объекта"""
        if self.shipping_conditions_combo.currentIndex() == 1:  # "Доставка до объекта"
            object_name = self.object_name_input.text().strip()
            if object_name and not self.delivery_address_input.text().strip():
                # Автозаполняем только если поле пустое
                self.delivery_address_input.setText(object_name)

    def handle_recalculate_kp_with_delivery(self):
        """Пересчет КП с распределением стоимости доставки"""
        delivery_cost = self.delivery_cost_input.value()
        
        if delivery_cost <= 0:
            QMessageBox.warning(
                self, "Предупреждение",
                "Введите сумму доставки больше нуля"
            )
            return
        
        items_count = self.cart_table.rowCount()
        if items_count == 0:
            QMessageBox.warning(
                self, "Предупреждение",
                "В корзине нет товаров для распределения доставки"
            )
            return
        
        # Распределяем стоимость доставки равными долями
        delivery_per_item = distribute_delivery_cost(delivery_cost, items_count)
        
        # Добавляем стоимость доставки к каждой позиции
        for row in range(items_count):
            # Получаем текущую цену за единицу
            price_item = self.cart_table.item(row, 3)
            if not price_item:
                continue
            
            original_price = price_item.data(Qt.UserRole) or 0
            # Добавляем стоимость доставки к цене
            new_price = original_price + delivery_per_item
            
            # Обновляем цену за единицу
            price_item.setText(format_price_with_spaces(new_price))
            price_item.setData(Qt.UserRole, new_price)
            
            # Обновляем цену со скидкой и итого
            self.update_cart_item_total(row)
        
        QMessageBox.information(
            self, "Успешно",
            f"Стоимость доставки ({format_price_with_spaces(delivery_cost)} ₽) "
            f"распределена равными долями ({format_price_with_spaces(delivery_per_item)} ₽ на позицию)"
        )
