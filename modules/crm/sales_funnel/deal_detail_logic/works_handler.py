"""
MODULE: modules.crm.sales_funnel.deal_detail_logic.works_handler
RESPONSIBILITY: Manage Works table logic in Deal Card.
ALLOWED: PyQt5, loguru, modules.crm.sales_funnel.deal_item_repository.
FORBIDDEN: Mixing logic with other item types.
ERRORS: None.

Модуль для работы с работами в детальной карточке сделки.

Содержит методы для добавления, редактирования и сохранения работ.
"""

from typing import Optional
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QLabel, QMessageBox
from loguru import logger

from modules.crm.sales_funnel.deal_detail_service import DealDetailService


class WorksHandler:
    """Класс для обработки работ из проектной документации."""
    
    def __init__(self, works_table: QTableWidget, works_total_label: QLabel,
                 deal_id: int, detail_service: DealDetailService, parent_dialog):
        self.works_table = works_table
        self.works_total_label = works_total_label
        self.deal_id = deal_id
        self.detail_service = detail_service
        self.parent_dialog = parent_dialog
        self._updating = False
    
    def add_row(self) -> None:
        """Добавление новой строки в таблицу работ."""
        row_count = self.works_table.rowCount()
        self.works_table.insertRow(row_count)
        # Устанавливаем значения по умолчанию
        self.works_table.setItem(row_count, 1, QTableWidgetItem("1"))  # Объем
        self.works_table.setItem(row_count, 2, QTableWidgetItem("шт"))  # Ед.
        self.works_table.setItem(row_count, 3, QTableWidgetItem("0"))  # Цена
        self.works_table.setItem(row_count, 4, QTableWidgetItem("0.00"))  # Итого
    
    def on_item_changed(self, item: QTableWidgetItem) -> None:
        """Обработка изменения ячейки в таблице работ."""
        if self._updating:
            return
        
        row = item.row()
        col = item.column()
        
        # Пересчитываем итого для строки, если изменились Объем или Цена
        if col in (1, 3):  # Объем или Цена
            self.recalculate_row(row)
        
        # Обновляем общий итог
        self.update_total()
    
    def recalculate_row(self, row: int) -> None:
        """Пересчет итого для строки работ."""
        try:
            self._updating = True
            
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
            self._updating = False
    
    def update_total(self) -> None:
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
    
    def save(self) -> None:
        """Сохранение работ в БД."""
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
            success = repo.save_items(self.deal_id, works, "работа")
            
            if success:
                QMessageBox.information(self.parent_dialog, "Успех", f"Сохранено {len(works)} работ")
                # Уведомляем родителя для обновления сравнения цен
                if hasattr(self.parent_dialog, '_update_price_comparison'):
                    self.parent_dialog._update_price_comparison()
            else:
                QMessageBox.warning(self.parent_dialog, "Ошибка", "Не удалось сохранить работы")
        except Exception as exc:
            logger.error(f"Ошибка при сохранении работ: {exc}", exc_info=True)
            QMessageBox.critical(self.parent_dialog, "Ошибка", f"Не удалось сохранить работы: {exc}")
    
    def load_from_db(self) -> None:
        """Загрузка работ из БД."""
        from modules.crm.sales_funnel.deal_item_repository import DealItemRepository
        
        repo = DealItemRepository(self.detail_service.db_manager)
        works = repo.get_items_by_deal(self.deal_id, "работа")
        
        # Заполняем таблицу работ
        self._updating = True
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
            self.add_row()
        
        self._updating = False
        self.update_total()

