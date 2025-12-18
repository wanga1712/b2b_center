"""
Модуль для управления ОКПД кодами в настройках.
"""

from typing import Optional
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QMessageBox, QInputDialog
from PyQt5.QtCore import Qt
from loguru import logger

from services.tender_repository import TenderRepository


class OKPDManager:
    """Класс для управления ОКПД кодами"""
    
    def __init__(self, tender_repo: TenderRepository, user_id: int):
        """
        Инициализация менеджера ОКПД
        
        Args:
            tender_repo: Репозиторий для работы с тендерами
            user_id: ID пользователя
        """
        self.tender_repo = tender_repo
        self.user_id = user_id
    
    def load_okpd_codes(self, okpd_results_list: QListWidget, region_combo=None, search_text: Optional[str] = None):
        """Загрузка списка ОКПД кодов с учетом выбранного региона"""
        if not self.tender_repo:
            logger.warning("Репозиторий закупок не инициализирован, ОКПД не загружены")
            return
        
        if okpd_results_list is None:
            logger.warning("okpd_results_list не инициализирован (None)")
            return
        
        try:
            okpd_results_list.clear()
            
            # Получаем выбранный регион
            region_id = None
            if region_combo and region_combo.currentIndex() > 0:
                region_data = region_combo.currentData()
                if region_data:
                    region_id = region_data.get('id')
                    logger.debug(f"Выбран регион с ID: {region_id}")
            
            # Поиск с учетом региона
            if search_text:
                logger.debug(f"Поиск ОКПД по тексту: {search_text}, регион: {region_id}")
                okpd_codes = self.tender_repo.search_okpd_codes_by_region(
                    search_text=search_text,
                    region_id=region_id,
                    limit=100
                )
            else:
                if region_id:
                    logger.debug(f"Загрузка ОКПД для региона: {region_id}")
                    okpd_codes = self.tender_repo.search_okpd_codes_by_region(
                        search_text=None,
                        region_id=region_id,
                        limit=100
                    )
                else:
                    logger.debug("Загрузка всех ОКПД")
                    okpd_codes = self.tender_repo.get_all_okpd_codes(limit=100)
            
            logger.info(f"Загружено ОКПД кодов: {len(okpd_codes)}")
            
            for okpd in okpd_codes:
                code = okpd.get('sub_code') or okpd.get('main_code', '')
                name = okpd.get('name', 'Без названия')
                
                item_text = f"{code} - {name[:80]}" if name else code
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, okpd)
                okpd_results_list.addItem(item)
            
            if len(okpd_codes) == 0:
                no_results_item = QListWidgetItem("ОКПД коды не найдены")
                no_results_item.setFlags(no_results_item.flags() & ~Qt.ItemIsSelectable)
                okpd_results_list.addItem(no_results_item)
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке ОКПД кодов: {e}")
            error_item = QListWidgetItem(f"Ошибка загрузки: {str(e)}")
            error_item.setFlags(error_item.flags() & ~Qt.ItemIsSelectable)
            okpd_results_list.addItem(error_item)
    
    def add_okpd(self, okpd_results_list: QListWidget, parent_widget=None):
        """Обработка добавления выбранного ОКПД с возможностью выбора категории"""
        if not self._validate_repo(parent_widget):
            return
        
        okpd_data, okpd_code = self._get_selected_okpd(okpd_results_list, parent_widget)
        if not okpd_data or not okpd_code:
            return
        
        category_id = self._select_category(okpd_code, parent_widget)
        was_existing, existing_category_id = self._check_existing_okpd(okpd_code)
        
        okpd_id = self._add_okpd_code(okpd_code, okpd_data.get('name'), parent_widget)
        if not okpd_id:
            return
        
        if category_id:
            self._assign_category(okpd_id, category_id, okpd_code, was_existing, existing_category_id, parent_widget)
        else:
            self._show_add_result(okpd_code, was_existing, parent_widget)
    
    def _validate_repo(self, parent_widget) -> bool:
        """Проверка наличия репозитория"""
        if not self.tender_repo:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", "Нет подключения к базе данных")
            return False
        return True
    
    def _get_selected_okpd(self, okpd_results_list: QListWidget, parent_widget) -> tuple:
        """Получение выбранного ОКПД из списка"""
        current_item = okpd_results_list.currentItem()
        if not current_item:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Предупреждение", "Выберите код ОКПД из списка")
            return None, None
        
        okpd_data = current_item.data(Qt.UserRole)
        if not okpd_data:
            return None, None
        
        okpd_code = okpd_data.get('sub_code') or okpd_data.get('main_code', '')
        if not okpd_code:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", "Не удалось определить код ОКПД")
            return None, None
        
        return okpd_data, okpd_code
    
    def _select_category(self, okpd_code: str, parent_widget) -> Optional[int]:
        """Выбор категории для ОКПД кода"""
        categories = self.tender_repo.get_okpd_categories(self.user_id)
        if not categories or not parent_widget:
            return None
        
        category_names = [cat.get('name', 'Без названия') for cat in categories]
        category_names.insert(0, "Без категории")
        
        selected, ok = QInputDialog.getItem(
            parent_widget,
            "Выбор категории",
            f"Выберите категорию для ОКПД кода {okpd_code}:",
            category_names,
            0,
            False
        )
        
        if ok and selected != "Без категории":
            for cat in categories:
                if cat.get('name') == selected:
                    return cat.get('id')
        return None
    
    def _check_existing_okpd(self, okpd_code: str) -> tuple:
        """Проверка существования ОКПД кода"""
        from psycopg2.extras import RealDictCursor
        
        check_query = """
            SELECT id, category_id FROM okpd_from_users 
            WHERE user_id = %s AND okpd_code = %s
        """
        existing_check = self.tender_repo.db_manager.execute_query(
            check_query,
            (self.user_id, okpd_code),
            RealDictCursor
        )
        
        was_existing = bool(existing_check)
        existing_category_id = existing_check[0].get('category_id') if existing_check else None
        return was_existing, existing_category_id
    
    def _add_okpd_code(self, okpd_code: str, name: Optional[str], parent_widget) -> Optional[int]:
        """Добавление ОКПД кода"""
        okpd_id = self.tender_repo.add_user_okpd_code(
            user_id=self.user_id,
            okpd_code=okpd_code,
            name=name
        )
        
        if not okpd_id and parent_widget:
            QMessageBox.warning(parent_widget, "Ошибка", "Не удалось добавить код ОКПД")
        return okpd_id
    
    def _assign_category(self, okpd_id: int, category_id: int, okpd_code: str, 
                        was_existing: bool, existing_category_id: Optional[int], parent_widget):
        """Привязка категории к ОКПД коду"""
        success = self.tender_repo.assign_okpd_to_category(
            user_id=self.user_id,
            okpd_id=okpd_id,
            category_id=category_id
        )
        
        if success and parent_widget:
            if was_existing:
                if existing_category_id == category_id:
                    QMessageBox.information(
                        parent_widget, 
                        "Информация", 
                        f"Код ОКПД {okpd_code} уже был добавлен с этой категорией."
                    )
                else:
                    QMessageBox.information(
                        parent_widget, 
                        "Успех", 
                        f"Код ОКПД {okpd_code} уже был добавлен. Категория обновлена."
                    )
            else:
                QMessageBox.information(
                    parent_widget, 
                    "Успех", 
                    f"Код ОКПД {okpd_code} добавлен и привязан к категории"
                )
    
    def _show_add_result(self, okpd_code: str, was_existing: bool, parent_widget):
        """Отображение результата добавления ОКПД"""
        if not parent_widget:
            return
        
        if was_existing:
            QMessageBox.information(
                parent_widget, 
                "Информация", 
                f"Код ОКПД {okpd_code} уже был добавлен ранее."
            )
        else:
            QMessageBox.information(parent_widget, "Успех", f"Код ОКПД {okpd_code} добавлен")
    
    def remove_okpd(self, okpd_id: int, parent_widget=None):
        """Обработка удаления ОКПД"""
        if not self.tender_repo:
            return
        
        if parent_widget:
            reply = QMessageBox.question(
                parent_widget,
                "Подтверждение",
                "Вы уверены, что хотите удалить этот код ОКПД?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
        
        success = self.tender_repo.remove_user_okpd_code(self.user_id, okpd_id)
        if success and parent_widget:
            QMessageBox.information(parent_widget, "Успех", "Код ОКПД удален")

