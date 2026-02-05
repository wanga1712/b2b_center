"""
MODULE: modules.crm.sales_funnel.deal_detail_logic.products_handler
RESPONSIBILITY: Manage Commercial Proposal (Products) table logic in Deal Card.
ALLOWED: PyQt5, loguru, modules.crm.sales_funnel.deal_item_repository.
FORBIDDEN: Mixing logic with other item types.
ERRORS: None.

Модуль для работы с товарами КП в детальной карточке сделки.

Содержит методы для добавления, редактирования и сохранения товаров из БД.
"""

from typing import Dict, Any
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QLabel, QMessageBox
from loguru import logger

from modules.crm.sales_funnel.deal_detail_service import DealDetailService
from modules.styles.general_styles import COLORS


class ProductsHandler:
    """Класс для обработки товаров КП из базы данных."""
    
    def __init__(self, products_table: QTableWidget, products_total_label: QLabel, comparison_label: QLabel,
                 materials_table: QTableWidget, works_table: QTableWidget,
                 deal_id: int, detail_service: DealDetailService, parent_dialog):
        self.products_table = products_table
        self.products_total_label = products_total_label
        self.comparison_label = comparison_label
        self.materials_table = materials_table
        self.works_table = works_table
        self.deal_id = deal_id
        self.detail_service = detail_service
        self.parent_dialog = parent_dialog
        self._updating = False
    
    def add_row(self) -> None:
        """Добавление новой строки в таблицу товаров из БД."""
        row_count = self.products_table.rowCount()
        self.products_table.insertRow(row_count)
        # Значения по умолчанию
        self.products_table.setItem(row_count, 2, QTableWidgetItem("1"))  # Кол-во
        self.products_table.setItem(row_count, 3, QTableWidgetItem("шт"))  # Ед.
        self.products_table.setItem(row_count, 4, QTableWidgetItem("0"))  # Цена
        self.products_table.setItem(row_count, 5, QTableWidgetItem("0.00"))  # Итого
    
    def on_item_changed(self, item: QTableWidgetItem) -> None:
        """Обработка изменения ячейки в таблице товаров."""
        if self._updating:
            return
        
        row = item.row()
        col = item.column()
        
        # Пересчитываем итого для строки, если изменились Кол-во или Цена
        if col in (2, 4):  # Кол-во или Цена
            self.recalculate_row(row)
        
        # Обновляем общий итог и сравнение
        self.update_total()
        self.update_price_comparison()
    
    def recalculate_row(self, row: int) -> None:
        """Пересчет итого для строки товаров."""
        try:
            self._updating = True
            
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
            self._updating = False
    
    def update_total(self) -> None:
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
    
    def update_price_comparison(self) -> None:
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
    
    def on_product_selected_from_search(self, row: int, product_data: dict) -> None:
        """Обработка выбора товара из автопоиска."""
        try:
            self._updating = True
            
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
            
            self.recalculate_row(row)
            self.update_total()
            self.update_price_comparison()
        finally:
            self._updating = False
    
    def save(self) -> None:
        """Сохранение товаров КП в БД."""
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
            success = repo.save_items(self.deal_id, products, "товар_кп")
            
            if success:
                QMessageBox.information(self.parent_dialog, "Успех", f"Сохранено {len(products)} товаров в КП")
            else:
                QMessageBox.warning(self.parent_dialog, "Ошибка", "Не удалось сохранить товары КП")
        except Exception as exc:
            logger.error(f"Ошибка при сохранении товаров КП: {exc}", exc_info=True)
            QMessageBox.critical(self.parent_dialog, "Ошибка", f"Не удалось сохранить товары КП: {exc}")
    
    def load_from_db(self) -> None:
        """Загрузка товаров КП из БД."""
        # #region agent log
        import json
        from datetime import datetime
        from pathlib import Path
        log_file = Path(r'c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log')
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'location': 'products_handler.py:load_from_db:entry',
                'message': 'Начало загрузки товаров из БД',
                'data': {
                    'deal_id': self.deal_id
                },
                'hypothesisId': 'H1',
                'sessionId': 'debug-session'
            }) + '\n')
        # #endregion agent log
        
        from modules.crm.sales_funnel.deal_item_repository import DealItemRepository
        
        repo = DealItemRepository(self.detail_service.db_manager)
        products_kp = repo.get_items_by_deal(self.deal_id, "товар_кп")
        
        # #region agent log
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'location': 'products_handler.py:load_from_db:after_query',
                'message': 'Товары загружены из БД',
                'data': {
                    'deal_id': self.deal_id,
                    'products_count': len(products_kp) if products_kp else 0,
                    'products_preview': str(products_kp[:2]) if products_kp else 'None'
                },
                'hypothesisId': 'H2',
                'sessionId': 'debug-session'
            }) + '\n')
        # #endregion agent log
        
        # Заполняем таблицу товаров КП
        self._updating = True
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
            self.add_row()
        
        self._updating = False
        self.update_total()
        self.update_price_comparison()

