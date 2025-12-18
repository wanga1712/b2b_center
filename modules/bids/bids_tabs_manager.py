"""
Менеджер для управления вкладками и обновлениями в BidsWidget

Отвечает за:
- Обновление текущей ленты закупок
- Обработку изменения категории фильтра
- Обработку нажатия кнопки "Показать тендеры"
- Обработку изменения выбора закупок
"""

from typing import Optional
from PyQt5.QtWidgets import QTabWidget, QMessageBox
from loguru import logger
from modules.bids.search_params_cache import SearchParamsCache
from modules.bids.bids_tender_loader import BidsTenderLoader
from modules.bids.tender_list_widget import TenderListWidget


class BidsTabsManager:
    """Менеджер для управления вкладками и обновлениями"""
    
    def __init__(
        self,
        tabs: QTabWidget,
        search_params_cache: SearchParamsCache,
        tender_loader: BidsTenderLoader,
        tenders_44fz_widget: TenderListWidget,
        tenders_223fz_widget: TenderListWidget,
        won_tenders_44fz_widget: Optional[TenderListWidget],
        won_tenders_223fz_widget: Optional[TenderListWidget],
        commission_tenders_44fz_widget: Optional[TenderListWidget],
        settings_tab,
        user_id: int,
        parent_widget
    ):
        """
        Инициализация менеджера вкладок
        
        Args:
            tabs: Виджет вкладок
            search_params_cache: Кэш параметров поиска
            tender_loader: Загрузчик тендеров
            tenders_44fz_widget: Виджет новых закупок 44ФЗ
            tenders_223fz_widget: Виджет новых закупок 223ФЗ
            won_tenders_44fz_widget: Виджет разыгранных закупок 44ФЗ
            won_tenders_223fz_widget: Виджет разыгранных закупок 223ФЗ
            commission_tenders_44fz_widget: Виджет закупок "Работа комиссии" 44ФЗ
            settings_tab: Вкладка настроек
            user_id: ID пользователя
            parent_widget: Родительский виджет
        """
        self.tabs = tabs
        self.search_params_cache = search_params_cache
        self.tender_loader = tender_loader
        self.tenders_44fz_widget = tenders_44fz_widget
        self.tenders_223fz_widget = tenders_223fz_widget
        self.won_tenders_44fz_widget = won_tenders_44fz_widget
        self.won_tenders_223fz_widget = won_tenders_223fz_widget
        self.commission_tenders_44fz_widget = commission_tenders_44fz_widget
        self.settings_tab = settings_tab
        self.user_id = user_id
        self.parent_widget = parent_widget
    
    def refresh_current_feed(self):
        """Обновление текущей ленты закупок"""
        current_index = self.tabs.currentIndex()
        tab_text = self.tabs.tabText(current_index)
        
        tab_config = self._get_tab_config(tab_text)
        if not tab_config:
            logger.info(f"Обновление недоступно для вкладки: {tab_text}")
            return
        
        logger.info(f"Обновление ленты {tab_text}...")
        self.search_params_cache.clear_tenders_cache(
            registry_type=tab_config['registry_type'],
            tender_type=tab_config['tender_type']
        )
        tab_config['load_method'](force=True)
        if tab_config.get('widget'):
            tab_config['widget']._loaded = True
    
    def on_category_filter_changed(self, index: int):
        """Обработка изменения категории фильтра - обновляем закупки"""
        if not self.tabs:
            return
        
        current_index = self.tabs.currentIndex()
        tab_text = self.tabs.tabText(current_index)
        tab_config = self._get_tab_config(tab_text)
        if tab_config and tab_config.get('load_method'):
            tab_config['load_method'](force=True)
    
    def handle_show_tenders(self):
        """
        Обработка нажатия кнопки 'Показать тендеры'
        
        Этот метод НЕ загружает данные - он только обновляет счетчики в подменю.
        Данные загружаются только при клике на конкретный раздел в подменю.
        """
        # Не загружаем данные здесь - только обновляем счетчики через PurchasesSubmenuWidget
        # Данные будут загружены при клике на конкретный раздел в подменю
        logger.info("Кнопка 'Показать тендеры' нажата - счетчики обновлены, данные будут загружены при клике на раздел")
    
    def on_tender_selection_changed(self, analyze_button):
        """Обработка изменения выбора закупок"""
        # Подсчитываем выбранные закупки из всех виджетов
        selected_44fz = self.tenders_44fz_widget.get_selected_tenders() if hasattr(self.tenders_44fz_widget, 'get_selected_tenders') else []
        selected_223fz = self.tenders_223fz_widget.get_selected_tenders() if hasattr(self.tenders_223fz_widget, 'get_selected_tenders') else []
        
        # Добавляем выбранные из разыгранных контрактов
        if self.won_tenders_44fz_widget:
            selected_44fz.extend(self.won_tenders_44fz_widget.get_selected_tenders() if hasattr(self.won_tenders_44fz_widget, 'get_selected_tenders') else [])
        if self.won_tenders_223fz_widget:
            selected_223fz.extend(self.won_tenders_223fz_widget.get_selected_tenders() if hasattr(self.won_tenders_223fz_widget, 'get_selected_tenders') else [])
        # Добавляем выбранные из закупок "Работа комиссии"
        if self.commission_tenders_44fz_widget:
            selected_44fz.extend(self.commission_tenders_44fz_widget.get_selected_tenders() if hasattr(self.commission_tenders_44fz_widget, 'get_selected_tenders') else [])
        
        total_selected = len(selected_44fz) + len(selected_223fz)
        
        # Включаем/выключаем кнопку анализа
        if analyze_button:
            analyze_button.setEnabled(total_selected > 0)
            if total_selected > 0:
                analyze_button.setText(f"📄 Анализ выбранных ({total_selected})")
            else:
                analyze_button.setText("📄 Анализ выбранных")
    
    def _get_tab_config(self, tab_text: str) -> Optional[dict]:
        """Получение конфигурации для вкладки"""
        tab_configs = {
            "Новые закупки 44ФЗ": {
                'registry_type': '44fz',
                'tender_type': 'new',
                'widget': self.tenders_44fz_widget,
                'load_method': self._load_tenders_44fz
            },
            "Новые закупки 223ФЗ": {
                'registry_type': '223fz',
                'tender_type': 'new',
                'widget': self.tenders_223fz_widget,
                'load_method': self._load_tenders_223fz
            },
            "Разыгранные закупки 44ФЗ": {
                'registry_type': '44fz',
                'tender_type': 'won',
                'widget': self.won_tenders_44fz_widget,
                'load_method': self._load_won_tenders_44fz
            },
            "Разыгранные закупки 223ФЗ": {
                'registry_type': '223fz',
                'tender_type': 'won',
                'widget': self.won_tenders_223fz_widget,
                'load_method': self._load_won_tenders_223fz
            },
            "Работа комиссии 44 ФЗ": {
                'registry_type': '44fz',
                'tender_type': 'commission',
                'widget': self.commission_tenders_44fz_widget,
                'load_method': self._load_commission_tenders_44fz
            }
        }
        return tab_configs.get(tab_text)
    
    def _load_tenders(self, loader_method, widget, force: bool = False):
        """Общий метод загрузки тендеров"""
        if not widget:
            return
        category_filter_combo = self.settings_tab.get_category_filter_combo() if self.settings_tab else None
        loader_method(
            widget=widget,
            user_id=self.user_id,
            category_filter_combo=category_filter_combo,
            force=force,
            parent_widget=self.parent_widget
        )
    
    def _load_tenders_44fz(self, force: bool = False):
        """Загрузка новых закупок 44ФЗ"""
        self._load_tenders(self.tender_loader.load_tenders_44fz, self.tenders_44fz_widget, force)
    
    def _load_tenders_223fz(self, force: bool = False):
        """Загрузка новых закупок 223ФЗ"""
        self._load_tenders(self.tender_loader.load_tenders_223fz, self.tenders_223fz_widget, force)
    
    def _load_won_tenders_44fz(self, force: bool = False):
        """Загрузка разыгранных закупок 44ФЗ"""
        self._load_tenders(self.tender_loader.load_won_tenders_44fz, self.won_tenders_44fz_widget, force)
    
    def _load_won_tenders_223fz(self, force: bool = False):
        """Загрузка разыгранных закупок 223ФЗ"""
        self._load_tenders(self.tender_loader.load_won_tenders_223fz, self.won_tenders_223fz_widget, force)
    
    def _load_commission_tenders_44fz(self, force: bool = False):
        """Загрузка закупок 44ФЗ со статусом 'Работа комиссии'"""
        self._load_tenders(self.tender_loader.load_commission_tenders_44fz, self.commission_tenders_44fz_widget, force)

