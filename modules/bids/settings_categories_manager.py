"""
Модуль для управления категориями ОКПД в настройках.
"""

from PyQt5.QtWidgets import QMessageBox, QComboBox, QListWidget
from PyQt5.QtCore import Qt
from loguru import logger

from services.tender_repository import TenderRepository


class CategoriesManager:
    """Класс для управления категориями ОКПД"""
    
    def __init__(self, tender_repo: TenderRepository, user_id: int):
        """
        Инициализация менеджера категорий
        
        Args:
            tender_repo: Репозиторий для работы с тендерами
            user_id: ID пользователя
        """
        self.tender_repo = tender_repo
        self.user_id = user_id
    
    def load_categories(self, categories_list: QListWidget = None, category_filter_combo: QComboBox = None):
        """Загрузка и отображение категорий ОКПД пользователя"""
        if not self.tender_repo:
            return
        
        try:
            categories = self.tender_repo.get_okpd_categories(self.user_id)
            
            # Загружаем в список категорий
            if categories_list:
                categories_list.clear()
                for category in categories:
                    category_name = category.get('name', 'Без названия')
                    item_text = f"{category_name}"
                    if category.get('description'):
                        item_text += f" - {category.get('description')[:50]}"
                    
                    item = categories_list.item(categories_list.count())
                    if item is None:
                        item = categories_list.item(categories_list.count() - 1)
                    if item is None:
                        from PyQt5.QtWidgets import QListWidgetItem
                        item = QListWidgetItem(item_text)
                    else:
                        item.setText(item_text)
                    item.setData(Qt.UserRole, category)
                    if item not in [categories_list.item(i) for i in range(categories_list.count())]:
                        categories_list.addItem(item)
            
            # Загружаем в комбобокс фильтра
            if category_filter_combo:
                current_data = category_filter_combo.currentData()
                category_filter_combo.clear()
                category_filter_combo.addItem("Все категории", None)
                for category in categories:
                    category_name = category.get('name', 'Без названия')
                    category_id = category.get('id')
                    category_filter_combo.addItem(category_name, category_id)
                
                # Восстанавливаем выбранную категорию
                if current_data is not None:
                    for i in range(category_filter_combo.count()):
                        if category_filter_combo.itemData(i) == current_data:
                            category_filter_combo.setCurrentIndex(i)
                            break
        except Exception as e:
            logger.error(f"Ошибка при загрузке категорий ОКПД: {e}")
    
    def create_category(self, category_name: str, parent_widget=None):
        """Обработка создания новой категории ОКПД"""
        if not self.tender_repo:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", "Нет подключения к базе данных")
            return None
        
        category_name = category_name.strip()
        if not category_name:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Предупреждение", "Введите название категории")
            return None
        
        category_id = self.tender_repo.create_okpd_category(
            user_id=self.user_id,
            name=category_name
        )
        
        if category_id:
            if parent_widget:
                QMessageBox.information(parent_widget, "Успех", f"Категория '{category_name}' создана")
            return category_id
        else:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", "Не удалось создать категорию")
            return None
    
    def delete_category(self, categories_list: QListWidget, parent_widget=None):
        """Обработка удаления категории ОКПД"""
        if not self.tender_repo:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", "Нет подключения к базе данных")
            return False
        
        current_item = categories_list.currentItem()
        if not current_item:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Предупреждение", "Выберите категорию для удаления")
            return False
        
        category_data = current_item.data(Qt.UserRole)
        if not category_data:
            return False
        
        category_id = category_data.get('id')
        category_name = category_data.get('name', 'категория')
        
        if parent_widget:
            reply = QMessageBox.question(
                parent_widget,
                "Подтверждение",
                f"Вы уверены, что хотите удалить категорию '{category_name}'?\n\nОКПД коды из этой категории останутся, но будут отвязаны от категории.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return False
        
        success = self.tender_repo.delete_okpd_category(category_id, self.user_id)
        if success and parent_widget:
            QMessageBox.information(parent_widget, "Успех", f"Категория '{category_name}' удалена")
        
        return success

