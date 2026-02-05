"""
MODULE: modules.crm.sales_funnel.deal_detail_logic.materials_handler
RESPONSIBILITY: Manage Materials table logic in Deal Card.
ALLOWED: PyQt5, loguru, modules.crm.sales_funnel.deal_item_repository.
FORBIDDEN: Mixing logic with other item types (Works, Products).
ERRORS: None.

Модуль для работы с материалами в детальной карточке сделки.

Содержит методы для добавления, редактирования и сохранения материалов.
"""

from typing import Optional
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QLabel, QMessageBox
from loguru import logger

from modules.crm.sales_funnel.deal_detail_service import DealDetailService
from modules.styles.general_styles import COLORS


class MaterialsHandler:
    """Класс для обработки материалов из проектной документации."""
    
    def __init__(self, materials_table: QTableWidget, materials_total_label: QLabel,
                 deal_id: int, detail_service: DealDetailService, parent_dialog):
        self.materials_table = materials_table
        self.materials_total_label = materials_total_label
        self.deal_id = deal_id
        self.detail_service = detail_service
        self.parent_dialog = parent_dialog
        self._updating = False
    
    def add_row(self) -> None:
        """Добавление новой строки в таблицу материалов."""
        row_count = self.materials_table.rowCount()
        self.materials_table.insertRow(row_count)
        # Устанавливаем значения по умолчанию
        self.materials_table.setItem(row_count, 1, QTableWidgetItem("1"))  # Кол-во
        self.materials_table.setItem(row_count, 2, QTableWidgetItem("шт"))  # Ед.
        self.materials_table.setItem(row_count, 3, QTableWidgetItem("0"))  # Цена
        self.materials_table.setItem(row_count, 4, QTableWidgetItem("0.00"))  # Итого
    
    def on_item_changed(self, item: QTableWidgetItem) -> None:
        """Обработка изменения ячейки в таблице материалов."""
        if self._updating:
            return
        
        row = item.row()
        col = item.column()
        
        # Пересчитываем итого для строки, если изменились Кол-во или Цена
        if col in (1, 3):  # Кол-во или Цена
            self.recalculate_row(row)
        
        # Обновляем общий итог
        self.update_total()
    
    def recalculate_row(self, row: int) -> None:
        """Пересчет итого для строки материалов."""
        try:
            self._updating = True
            
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
            self._updating = False
    
    def update_total(self) -> None:
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
    
    def save(self) -> None:
        """Сохранение материалов в БД."""
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
            success = repo.save_items(self.deal_id, materials, "материал")
            
            if success:
                QMessageBox.information(self.parent_dialog, "Успех", f"Сохранено {len(materials)} материалов")
            else:
                QMessageBox.warning(self.parent_dialog, "Ошибка", "Не удалось сохранить материалы")
        except Exception as exc:
            logger.error(f"Ошибка при сохранении материалов: {exc}", exc_info=True)
            QMessageBox.critical(self.parent_dialog, "Ошибка", f"Не удалось сохранить материалы: {exc}")
    
    def load_from_db(self) -> None:
        """Загрузка материалов из БД."""
        from modules.crm.sales_funnel.deal_item_repository import DealItemRepository
        
        repo = DealItemRepository(self.detail_service.db_manager)
        materials = repo.get_items_by_deal(self.deal_id, "материал")
        
        # Заполняем таблицу материалов
        self._updating = True
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
            self.add_row()
        
        self._updating = False
        self.update_total()

