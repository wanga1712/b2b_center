"""
Редактирование товаров в каталоге
"""

from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QMessageBox, QDialog
from PyQt5.QtCore import Qt
from loguru import logger
from modules.kp.weight_edit_dialog import WeightEditDialog
from modules.kp.price_edit_dialog import PriceEditDialog
from modules.kp.name_edit_dialog import NameEditDialog
from modules.kp.unit_edit_dialog import UnitEditDialog
from modules.kp.logic import get_unit_display_name
from modules.kp.formatters import convert_price_to_rubles, format_price_with_spaces


class ProductEditor:
    """Редактирование товаров в каталоге"""
    
    def __init__(
        self,
        product_table: QTableWidget,
        product_repo,
        refresh_callback
    ):
        """
        Args:
            product_table: Таблица товаров
            product_repo: Репозиторий товаров
            refresh_callback: Функция для обновления каталога
        """
        self.product_table = product_table
        self.product_repo = product_repo
        self.refresh_callback = refresh_callback
    
    def edit_name(self, row: int, parent_widget) -> None:
        """Редактирование наименования товара"""
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
                parent_widget, "Ошибка",
                "Не удалось определить идентификатор товара"
            )
            return
        
        dialog = NameEditDialog(current_name, parent_widget)
        if dialog.exec_() == QDialog.Accepted:
            new_name = dialog.get_name()
            
            if self.product_repo and self.product_repo.update_product_name(product_id, new_name):
                name_item.setText(new_name)
                name_item.setToolTip(new_name)
                product_data['name'] = new_name
                name_item.setData(Qt.UserRole, product_data)
                
                QMessageBox.information(
                    parent_widget, "Успешно",
                    f"Наименование товара обновлено: {new_name}"
                )
                self.refresh_callback()
            else:
                QMessageBox.critical(
                    parent_widget, "Ошибка",
                    "Не удалось обновить наименование товара в базе данных"
                )
    
    def edit_unit(self, row: int, parent_widget) -> None:
        """Редактирование единицы измерения товара"""
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
                parent_widget, "Ошибка",
                "Не удалось определить идентификатор цены товара"
            )
            return
        
        dialog = UnitEditDialog(
            current_container_type or '',
            current_size or '',
            product_name,
            parent_widget
        )
        if dialog.exec_() == QDialog.Accepted:
            new_container_type = dialog.get_container_type()
            new_size = dialog.get_size()
            
            if self.product_repo and self.product_repo.update_product_unit(
                pricing_id, new_container_type, new_size
            ):
                # Формируем новую единицу измерения
                if new_container_type and new_size:
                    unit = f"{new_container_type} {new_size}".replace(' - ', ' ').replace('- ', '').strip()
                elif new_container_type:
                    unit = new_container_type
                elif new_size:
                    unit = new_size
                else:
                    unit = "шт"
                
                unit_item = self.product_table.item(row, 1)
                if unit_item:
                    unit_item.setText(unit)
                
                product_data['container_type'] = new_container_type
                product_data['size'] = new_size
                name_item.setData(Qt.UserRole, product_data)
                
                QMessageBox.information(
                    parent_widget, "Успешно",
                    f"Единица измерения обновлена: {unit}"
                )
                self.refresh_callback()
            else:
                QMessageBox.critical(
                    parent_widget, "Ошибка",
                    "Не удалось обновить единицу измерения товара в базе данных"
                )
    
    def edit_weight(self, row: int, parent_widget) -> None:
        """Редактирование веса товара"""
        name_item = self.product_table.item(row, 0)
        if not name_item:
            return
        
        product_data = name_item.data(Qt.UserRole)
        if not product_data:
            return
        
        pricing_id = product_data.get('pricing_id')
        current_weight_raw = product_data.get('weight', 0.0)
        product_name = product_data.get('name', 'Товар')
        
        # Преобразуем вес в число, обрабатывая случаи, когда это строка (например, "-")
        try:
            if current_weight_raw is None:
                current_weight = 0.0
            elif isinstance(current_weight_raw, str):
                # Если строка, пытаемся преобразовать, иначе 0.0
                current_weight = float(current_weight_raw) if current_weight_raw.strip() and current_weight_raw != "-" else 0.0
            else:
                current_weight = float(current_weight_raw)
        except (ValueError, TypeError, AttributeError):
            current_weight = 0.0
        
        if not pricing_id:
            QMessageBox.warning(
                parent_widget, "Ошибка",
                "Не удалось определить идентификатор цены товара"
            )
            return

        dialog = WeightEditDialog(current_weight, product_name, parent_widget)
        if dialog.exec_() == QDialog.Accepted:
            new_weight = dialog.get_weight()
            
            # #region agent log
            try:
                from pathlib import Path
                import json
                from datetime import datetime

                log_entry = {
                    "sessionId": "debug-session",
                    "runId": "pre-fix",
                    "hypothesisId": "B",
                    "location": f"{__file__}:edit_weight:before_update",
                    "message": "Попытка обновления веса товара",
                    "data": {
                        "pricing_id": pricing_id,
                        "new_weight": float(new_weight),
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000),
                }
                log_path = Path(__file__).resolve().parents[2] / ".cursor" / "debug.log"
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion

            if self.product_repo and self.product_repo.update_product_weight(pricing_id, new_weight):
                # Обновляем отображение
                weight_item = self.product_table.item(row, 2)
                if weight_item:
                    weight_item.setText(f"{new_weight:.2f}")
                
                # Обновляем данные
                product_data['weight'] = new_weight
                name_item.setData(Qt.UserRole, product_data)
                
                # #region agent log
                try:
                    from pathlib import Path
                    import json
                    from datetime import datetime

                    log_entry = {
                        "sessionId": "debug-session",
                        "runId": "pre-fix",
                        "hypothesisId": "C",
                        "location": f"{__file__}:edit_weight:after_update",
                        "message": "Вес товара успешно обновлён",
                        "data": {
                            "pricing_id": pricing_id,
                            "saved_weight": float(new_weight),
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000),
                    }
                    log_path = Path(__file__).resolve().parents[2] / ".cursor" / "debug.log"
                    with log_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion

                QMessageBox.information(
                    parent_widget, "Успешно",
                    f"Вес товара обновлен: {new_weight:.2f} кг"
                )
                self.refresh_callback()
            else:
                QMessageBox.critical(
                    parent_widget, "Ошибка",
                    "Не удалось обновить вес товара в базе данных"
                )
    
    def edit_price(self, row: int, parent_widget) -> None:
        """Редактирование цены товара"""
        name_item = self.product_table.item(row, 0)
        if not name_item:
            return
        
        product_data = name_item.data(Qt.UserRole)
        if not product_data:
            return
        
        pricing_id = product_data.get('pricing_id')
        manufacturer_name = product_data.get('manufacturer_name', '')
        current_price = product_data.get('price', 0.0)
        
        if not pricing_id:
            QMessageBox.warning(
                parent_widget, "Ошибка",
                "Не удалось определить идентификатор цены товара"
            )
            return
        
        dialog = PriceEditDialog(current_price, parent_widget)
        if dialog.exec_() == QDialog.Accepted:
            new_price = dialog.get_price()
            
            if self.product_repo and self.product_repo.update_product_price(pricing_id, new_price):
                # Конвертируем цену в рубли если нужно
                price_rub = convert_price_to_rubles(new_price, manufacturer_name)
                
                # Обновляем отображение
                price_item = self.product_table.item(row, 3)
                if price_item:
                    price_item.setText(format_price_with_spaces(price_rub))
                
                # Обновляем данные
                product_data['price'] = new_price
                name_item.setData(Qt.UserRole, product_data)
                
                QMessageBox.information(
                    parent_widget, "Успешно",
                    f"Цена товара обновлена: {format_price_with_spaces(price_rub)} ₽"
                )
                self.refresh_callback()
            else:
                QMessageBox.critical(
                    parent_widget, "Ошибка",
                    "Не удалось обновить цену товара в базе данных"
                )

