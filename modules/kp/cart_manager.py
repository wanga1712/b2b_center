"""
Менеджер корзины коммерческого предложения
"""

from typing import Dict, Any, List
from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QPushButton, QWidget,
    QVBoxLayout, QSpinBox, QComboBox, QLabel
)
from PyQt5.QtCore import Qt
from loguru import logger
from modules.kp.logic import calculate_item_total
from modules.kp.formatters import format_price_with_spaces
from modules.styles.table_styles import (
    get_table_button_style, get_table_cell_widget_container_style
)
from modules.styles.general_styles import SIZES


class CartManager:
    """Управление корзиной коммерческого предложения"""
    
    def __init__(self, cart_table: QTableWidget, total_label: QLabel, cart_info_label: QLabel):
        """
        Args:
            cart_table: Таблица корзины
            total_label: Метка для отображения итоговой суммы
            cart_info_label: Метка для отображения информации о корзине
        """
        self.cart_table = cart_table
        self.total_label = total_label
        self.cart_info_label = cart_info_label
    
    def add_item(
        self,
        product_data: Dict[str, Any],
        quantity: int,
        price: float
    ) -> None:
        """
        Добавление товара в корзину
        
        Args:
            product_data: Данные товара
            quantity: Количество
            price: Цена за единицу
        """
        from modules.kp.logic import get_unit_display_name
        
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
        qty_spin.valueChanged.connect(lambda: self._update_item_total(row))
        self.cart_table.setCellWidget(row, 2, qty_spin)
        
        # Цена за единицу
        price_item = QTableWidgetItem(format_price_with_spaces(price))
        price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
        price_item.setData(Qt.UserRole, price)
        self.cart_table.setItem(row, 3, price_item)
        
        # Скидка (редактируемое через ComboBox)
        discount_combo = QComboBox()
        discount_combo.addItems(["0%", "3%", "5%", "10%", "15%", "20%"])
        discount_combo.currentIndexChanged.connect(lambda: self._update_item_total(row))
        self.cart_table.setCellWidget(row, 4, discount_combo)
        
        # Цена со скидкой
        price_disc_item = QTableWidgetItem(format_price_with_spaces(price))
        price_disc_item.setFlags(price_disc_item.flags() & ~Qt.ItemIsEditable)
        self.cart_table.setItem(row, 5, price_disc_item)
        
        # Итого
        total_item = QTableWidgetItem(format_price_with_spaces(price * quantity))
        total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
        self.cart_table.setItem(row, 6, total_item)
        
        # Кнопка удалить
        btn_remove = QPushButton("Удалить")
        btn_remove.setStyleSheet(get_table_button_style())
        btn_remove.clicked.connect(lambda checked, r=row: self.remove_item(r))
        
        # Контейнер для кнопки
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)
        button_layout.addWidget(btn_remove)
        button_layout.setAlignment(Qt.AlignCenter)
        button_container.setStyleSheet(get_table_cell_widget_container_style())
        
        row_height = self.cart_table.verticalHeader().defaultSectionSize()
        if row_height <= 0:
            row_height = SIZES['table_row_height']
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
        
        self._update_table_height()
        self.update_total()
        self.update_info()
    
    def remove_item(self, row: int) -> None:
        """
        Удаление позиции из корзины
        
        Args:
            row: Индекс строки для удаления
        """
        if 0 <= row < self.cart_table.rowCount():
            self.cart_table.removeRow(row)
            self.update_total()
            self.update_info()
            self._update_table_height()
        else:
            logger.warning(f"Попытка удалить несуществующую строку: {row}")
    
    def _update_item_total(self, row: int) -> None:
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
    
    def update_total(self) -> None:
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
                except (ValueError, AttributeError):
                    continue
        
        total_formatted = format_price_with_spaces(total)
        self.total_label.setText(f"Итого с НДС: {total_formatted} ₽")
    
    def update_info(self) -> None:
        """Обновление информации о количестве товаров в корзине"""
        count = self.cart_table.rowCount()
        if count == 1:
            text = "В корзине: 1 товар"
        elif count < 5:
            text = f"В корзине: {count} товара"
        else:
            text = f"В корзине: {count} товаров"
        self.cart_info_label.setText(text)
    
    def _update_table_height(self) -> None:
        """Динамическое обновление высоты таблицы"""
        row_count = self.cart_table.rowCount()
        
        if row_count == 0:
            min_height = self.cart_table.horizontalHeader().height() + 50
        else:
            visible_rows = min(max(row_count, 5), 20)
            min_height = (
                self.cart_table.horizontalHeader().height() + 
                (SIZES['table_row_height'] * visible_rows) + 
                20
            )
        
        self.cart_table.setMinimumHeight(min_height)
    
    def apply_discount_to_all(self, discount_text: str) -> None:
        """
        Применение глобальной скидки ко всем позициям
        
        Args:
            discount_text: Текст скидки (например, "5%")
        """
        for row in range(self.cart_table.rowCount()):
            discount_widget = self.cart_table.cellWidget(row, 4)
            if discount_widget:
                index = discount_widget.findText(discount_text)
                if index >= 0:
                    discount_widget.setCurrentIndex(index)
                else:
                    discount_widget.setCurrentIndex(0)
                self._update_item_total(row)

