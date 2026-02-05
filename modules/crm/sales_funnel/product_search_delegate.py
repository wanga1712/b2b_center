"""
MODULE: modules.crm.sales_funnel.product_search_delegate
RESPONSIBILITY: UI Delegate for product autosuggest/search in tables.
ALLOWED: PyQt5, loguru, services.product_repository, core.database, config.settings.
FORBIDDEN: Heavy business logic.
ERRORS: None.

Делегат для автопоиска товаров в таблице КП.
"""

from typing import List, Dict, Any, Optional
from PyQt5.QtWidgets import QStyledItemDelegate, QLineEdit, QCompleter, QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from loguru import logger
from services.product_services.product_repository_facade import ProductRepositoryFacade
from core.database import DatabaseManager
from config.settings import DatabaseConfig


class ProductSearchDelegate(QStyledItemDelegate):
    """Делегат для ячеек с автопоиском товаров."""
    
    product_selected = pyqtSignal(int, dict)  # row, product_data
    
    def __init__(self, db_config: DatabaseConfig, parent=None):
        super().__init__(parent)
        from core.database import DatabaseManager
        self.db_manager = DatabaseManager(db_config)
        self.product_repo = ProductRepositoryFacade(self.db_manager)
        self._editors = {}  # Кэш редакторов
    
    def createEditor(self, parent: QWidget, option, index) -> QLineEdit:
        """Создание редактора с автозаполнением."""
        editor = QLineEdit(parent)
        editor.setPlaceholderText("Начните вводить название товара...")
        
        # Создаем completer
        completer = QCompleter(editor)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setMaxVisibleItems(10)
        
        # Создаем модель для completer
        model = QStandardItemModel()
        completer.setModel(model)
        
        editor.setCompleter(completer)
        
        # Связываем изменение текста с поиском
        editor.textChanged.connect(lambda text: self._search_products(text, model, editor, index.row()))
        
        # При выборе из списка сохраняем данные товара
        completer.activated.connect(lambda text: self._on_product_selected(text, model, index.row()))
        
        self._editors[index.row()] = {
            "editor": editor,
            "completer": completer,
            "model": model,
            "products_cache": {}
        }
        
        return editor
    
    def _search_products(self, text: str, model: QStandardItemModel, editor: QLineEdit, row: int):
        """Поиск товаров по введенному тексту."""
        if len(text) < 2:
            model.clear()
            return
        
        try:
            # Ищем товары с ценами
            products = self.product_repo.search_products(search_text=text, limit=50)
            
            model.clear()
            products_cache = {}
            
            for product in products:
                # Получаем цену товара
                pricing = self.product_repo.get_product_pricing(product.get("id"))
                if not pricing:
                    continue
                
                # Формируем текст для отображения
                manufacturer = product.get("manufacturer_name", "")
                price = pricing[0].get("price_per_unit", 0) if pricing else 0
                unit = pricing[0].get("unit", "шт") if pricing else "шт"
                
                display_text = f"{product.get('name')} | {manufacturer} | {price:.2f} руб/{unit}"
                
                item = QStandardItem(display_text)
                model.appendRow(item)
                
                # Сохраняем данные товара для последующего использования
                products_cache[display_text] = {
                    "id": product.get("id"),
                    "name": product.get("name"),
                    "manufacturer": manufacturer,
                    "price": price,
                    "unit": unit,
                }
            
            # Обновляем кэш
            if row in self._editors:
                self._editors[row]["products_cache"] = products_cache
            
        except Exception as exc:
            logger.error(f"Ошибка при поиске товаров: {exc}", exc_info=True)
    
    def _on_product_selected(self, text: str, model: QStandardItemModel, row: int):
        """Обработка выбора товара из списка."""
        if row not in self._editors:
            return
        
        products_cache = self._editors[row]["products_cache"]
        if text in products_cache:
            product_data = products_cache[text]
            self.product_selected.emit(row, product_data)
            logger.info(f"Выбран товар: {product_data['name']}, цена: {product_data['price']}")
    
    def setEditorData(self, editor: QLineEdit, index):
        """Установка данных в редактор."""
        value = index.model().data(index, Qt.EditRole)
        editor.setText(str(value) if value else "")
    
    def setModelData(self, editor: QLineEdit, model, index):
        """Сохранение данных из редактора в модель."""
        model.setData(index, editor.text(), Qt.EditRole)

