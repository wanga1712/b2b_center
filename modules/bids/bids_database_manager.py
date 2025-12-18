"""
Модуль для управления подключением к БД в виджете закупок

Содержит методы для переподключения к БД и восстановления данных
"""

from loguru import logger
from PyQt5.QtWidgets import QMessageBox

from core.tender_database import TenderDatabaseManager
from core.exceptions import DatabaseConnectionError, DatabaseQueryError
from modules.bids.settings_okpd_manager import OKPDManager
from modules.bids.settings_stop_words_manager import StopWordsManager
from modules.bids.settings_categories_manager import CategoriesManager
from modules.bids.search_params_cache import SearchParamsCache
from services.tender_repository import TenderRepository
from services.tender_match_repository import TenderMatchRepository


class BidsDatabaseManager:
    """
    Класс для управления подключением к БД
    
    Инкапсулирует логику переподключения и восстановления данных
    """
    
    def __init__(
        self,
        tender_db_manager: TenderDatabaseManager,
        tender_repo: TenderRepository,
        tender_match_repo: TenderMatchRepository,
        user_id: int,
        search_params_cache: SearchParamsCache
    ):
        """
        Инициализация менеджера БД
        
        Args:
            tender_db_manager: Менеджер БД tender_monitor
            tender_repo: Репозиторий закупок
            tender_match_repo: Репозиторий результатов поиска
            user_id: ID пользователя
            search_params_cache: Кэш параметров поиска
        """
        self.tender_db_manager = tender_db_manager
        self.tender_repo = tender_repo
        self.tender_match_repo = tender_match_repo
        self.user_id = user_id
        self.search_params_cache = search_params_cache
    
    def handle_db_reconnection(self, parent_widget, cache_manager, settings_tab) -> None:
        """
        Обработка переподключения к БД с восстановлением параметров
        
        Args:
            parent_widget: Родительский виджет (для QMessageBox)
            cache_manager: Менеджер кэша для восстановления параметров
            settings_tab: Вкладка настроек для перезагрузки данных
        """
        try:
            logger.info("Попытка переподключения к БД tender_monitor...")
            
            # Закрываем старое подключение если есть
            if self.tender_db_manager and self.tender_db_manager.is_connected():
                try:
                    self.tender_db_manager.disconnect()
                except Exception:
                    pass
            
            # Переподключаемся
            if self.tender_db_manager:
                self.tender_db_manager.connect()
                logger.info("Переподключение к БД tender_monitor успешно")
                
                # Пересоздаем репозиторий с новым подключением
                from core.dependency_injection import container
                self.tender_repo = container.get_tender_repository()
                self.tender_match_repo = container.get_tender_match_repository()
                
                # Обновляем менеджеры с новым репозиторием
                if settings_tab:
                    settings_tab.okpd_manager = OKPDManager(self.tender_repo, self.user_id)
                    settings_tab.stop_words_manager = StopWordsManager(self.tender_repo, self.user_id)
                    settings_tab.categories_manager = CategoriesManager(self.tender_repo, self.user_id)
                    settings_tab.tender_repo = self.tender_repo
                
                # Восстанавливаем параметры поиска
                if cache_manager and settings_tab:
                    region_combo = getattr(settings_tab, 'region_combo', None)
                    category_combo = getattr(settings_tab, 'category_filter_combo', None)
                    okpd_search = getattr(settings_tab, 'okpd_search_input', None)
                    cache_manager.restore_all_search_params_from_cache(
                        region_combo, category_combo, okpd_search
                    )
                
                # Перезагружаем данные
                if settings_tab:
                    settings_tab._init_settings_data()
                
                logger.info("Данные перезагружены после переподключения")
            else:
                logger.error("tender_db_manager не инициализирован")
                
        except Exception as e:
            logger.error(f"Ошибка при переподключении к БД: {e}", exc_info=True)
            QMessageBox.warning(
                parent_widget,
                "Ошибка подключения",
                f"Не удалось переподключиться к базе данных:\n{e}\n\n"
                "Параметры поиска сохранены и будут восстановлены при следующем успешном подключении."
            )

