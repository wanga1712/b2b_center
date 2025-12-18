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
    apply_combobox_style, apply_frame_style, COLORS, FONT_SIZES, SIZES,
    apply_text_style_light_italic, apply_scroll_area_style,
    apply_text_color, apply_font_weight, apply_separator_style
)
from modules.styles.kp_styles import (
    apply_kp_widget_theme, apply_kp_info_frame_style,
    apply_kp_total_frame_style
)
from modules.styles.table_styles import (
    get_table_button_style, get_table_cell_widget_container_style
)

# Импортируем бизнес-логику
from modules.kp.logic import (
    calculate_packaging_quantity,
    calculate_item_total,
    calculate_quotation_total,
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
# Импортируем утилиты форматирования
from modules.kp.formatters import format_price_with_spaces, convert_price_to_rubles
# Импортируем менеджеры
from modules.kp.search_manager import SearchManager
from modules.kp.cart_manager import CartManager
from modules.kp.product_editor import ProductEditor
# Импортируем построитель UI
from modules.kp.ui_builder import build_kp_ui


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
        
        # Создаем UI через ui_builder
        ui_controls = build_kp_ui(
            self,
            on_search_changed=self._on_search_text_changed,
            on_category_changed=self._on_category_changed,
            on_subcategory_changed=self._on_subcategory_changed,
            on_filter_changed=self._on_filter_changed,
            on_selection_changed=self.handle_product_selection,
            on_double_click=self._on_cell_double_click,
            on_quantity_type_changed=self.handle_quantity_type_change,
            on_quantity_changed=self.update_quantity_calculation,
            on_add_clicked=self._on_add_to_cart,
            on_go_to_cart=lambda: self.tabs.setCurrentIndex(1),
            on_apply_discount=self._on_apply_discount,
            on_shipping_changed=self.handle_shipping_conditions_changed,
            on_delivery_address_update=self.update_delivery_address,
            on_recalculate=self.handle_recalculate_kp_with_delivery,
            update_cart_table_height=self.update_cart_table_height
        )
        
        # Присваиваем все виджеты к self
        self.tabs = ui_controls.tabs
        self.search_field = ui_controls.search_field
        self.category_combo = ui_controls.category_combo
        self.subcategory_combo = ui_controls.subcategory_combo
        self.manufacturer_combo = ui_controls.manufacturer_combo
        self.product_table = ui_controls.product_table
        self.quantity_type_combo = ui_controls.quantity_type_combo
        self.quantity_input = ui_controls.quantity_input
        self.weight_input = ui_controls.weight_input
        self.calculated_quantity_label = ui_controls.calculated_quantity_label
        self.btn_add = ui_controls.btn_add
        self.cart_info_label = ui_controls.cart_info_label
        self.cart_table = ui_controls.cart_table
        self.apply_global_discount = ui_controls.apply_global_discount
        self.apply_discount_btn = ui_controls.apply_discount_btn
        self.object_name_input = ui_controls.object_name_input
        self.company_name_input = ui_controls.company_name_input
        self.contact_person_input = ui_controls.contact_person_input
        self.kp_validity_lbl = ui_controls.kp_validity_lbl
        self.payment_conditions_lbl = ui_controls.payment_conditions_lbl
        self.delivery_term_lbl = ui_controls.delivery_term_lbl
        self.shipping_conditions_combo = ui_controls.shipping_conditions_combo
        self.delivery_address_frame = ui_controls.delivery_address_frame
        self.delivery_address_input = ui_controls.delivery_address_input
        self.delivery_cost_input = ui_controls.delivery_cost_input
        self.recalculate_kp_btn = ui_controls.recalculate_kp_btn
        self.total_lbl = ui_controls.total_lbl
        
        # Исправляем подключение сигнала для обновления адреса доставки
        self.object_name_input.textChanged.connect(self.update_delivery_address)
        
        self.load_initial_data()
        
        # Инициализируем менеджеры после создания UI
        self.search_manager = SearchManager(
            self.product_repo,
            self.display_products,
            debounce_ms=300
        )
        self.cart_manager = CartManager(
            self.cart_table,
            self.total_lbl,
            self.cart_info_label
        )
        self.product_editor = ProductEditor(
            self.product_table,
            self.product_repo,
            self._refresh_search
        )
        
        self.load_all_products()


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
        if not hasattr(self, 'search_manager'):
            return
        
        # Используем search_manager для загрузки всех товаров
        self.search_manager.search()

    def _on_category_changed(self):
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
        self._on_filter_changed()

    def _on_subcategory_changed(self):
        """Обработка изменения подкатегории"""
        self._on_filter_changed()

    def _on_search_text_changed(self):
        """Обработка изменения текста поиска"""
        self._on_filter_changed()

    def _on_filter_changed(self):
        """Обработка изменения фильтров"""
        if not hasattr(self, 'search_manager'):
            return
        
        category_id = self.category_combo.currentData()
        subcategory_id = self.subcategory_combo.currentData()
        manufacturer_id = self.manufacturer_combo.currentData()
        search_text = self.search_field.text().strip() or None
        
        self.search_manager.search(
            category_id=category_id,
            subcategory_id=subcategory_id,
            manufacturer_id=manufacturer_id,
            search_text=search_text
        )
    
    def _refresh_search(self):
        """Обновление поиска (для использования в product_editor)"""
        self._on_filter_changed()

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

    def _on_cell_double_click(self, item: QTableWidgetItem):
        """Обработка двойного клика на ячейку таблицы"""
        if not hasattr(self, 'product_editor'):
            return
        
        row = item.row()
        column = item.column()
        
        # Редактирование наименования (колонка 0)
        if column == 0:
            self.product_editor.edit_name(row, self)
        # Редактирование единицы измерения (колонка 1)
        elif column == 1:
            self.product_editor.edit_unit(row, self)
        # Редактирование веса (колонка 2)
        elif column == 2:
            self.product_editor.edit_weight(row, self)
        # Редактирование цены (колонка 3)
        elif column == 3:
            self.product_editor.edit_price(row, self)
    

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


    def update_cart_table_height(self):
        """
        Обновление высоты таблицы корзины.
        
        Вызывается из UI‑построителя после создания таблицы корзины.
        Делегирует реальный пересчет высоты менеджеру корзины, если он уже инициализирован.
        """
        if hasattr(self, "cart_manager"):
            # Используем логику CartManager для расчета высоты
            try:
                self.cart_manager._update_table_height()  # type: ignore[attr-defined]
            except Exception:
                # В случае любой ошибки не падаем, чтобы не ломать запуск UI
                pass


    def _on_add_to_cart(self):
        """
        Обработчик нажатия на кнопку добавления товара в корзину.
        
        Использует выбранный товар, тип ввода количества и текущие значения
        полей количества/веса для добавления позиции в корзину через CartManager.
        """
        if not hasattr(self, "cart_manager"):
            return

        if not self.selected_product_data:
            QMessageBox.warning(self, "Выбор товара", "Сначала выберите товар из списка.")
            return

        # Определяем количество в зависимости от типа ввода
        is_weight_input = self.quantity_type_combo.currentIndex() == 1
        product_weight_raw = self.selected_product_data.get("weight", 0)

        try:
            product_weight = float(product_weight_raw) if product_weight_raw else 0
        except (ValueError, TypeError):
            product_weight = 0

        if is_weight_input:
            # Ввод по весу
            input_weight = self.weight_input.value()
            if input_weight <= 0:
                QMessageBox.warning(self, "Количество", "Введите положительное значение веса.")
                return
            if product_weight <= 0:
                QMessageBox.warning(
                    self,
                    "Данные товара",
                    "Для выбранного товара не задан вес упаковки, расчет невозможен.",
                )
                return
            quantity = calculate_packaging_quantity(input_weight, product_weight)
        else:
            # Ввод по количеству
            quantity = self.quantity_input.value()
            if quantity <= 0:
                QMessageBox.warning(self, "Количество", "Количество должно быть больше нуля.")
                return

        # Получаем цену товара (уже в рублях из display_products)
        price_raw = self.selected_product_data.get("price", 0)
        try:
            price = float(price_raw) if price_raw else 0
        except (ValueError, TypeError):
            price = 0

        if price <= 0:
            QMessageBox.warning(
                self,
                "Цена товара",
                "Для выбранного товара не задана корректная цена.",
            )
            return

        # Добавляем позицию в корзину
        self.cart_manager.add_item(self.selected_product_data, int(quantity), price)


    def _on_apply_discount(self):
        """Применение глобальной скидки ко всем позициям"""
        if not hasattr(self, 'cart_manager'):
            return
        
        disc_txt = self.apply_global_discount.currentText()
        self.cart_manager.apply_discount_to_all(disc_txt)

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
