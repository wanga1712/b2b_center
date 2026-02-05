"""
MODULE: modules.crm.home_widget
RESPONSIBILITY: Main CRM dashboard navigation with folders.
ALLOWED: PyQt5, loguru, modules.styles.*, modules.crm.*, modules.bids.*, modules.crm.sales_funnel.*.
FORBIDDEN: Direct SQL queries (use repositories).
ERRORS: None.

Главный виджет раздела CRM

Отображает папки с пиктограммами (как в "Мой компьютер") для навигации по подразделам CRM.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame, QScrollArea, QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont, QPixmap, QMovie
from pathlib import Path
from typing import Dict, Callable, Optional
from loguru import logger

from modules.styles.general_styles import (
    apply_label_style, apply_frame_style, COLORS, SIZES, FONT_SIZES, FONT_FAMILY
)
from modules.crm.folder_card import FolderCard
from modules.crm.purchases_submenu_widget import PurchasesSubmenuWidget
from modules.crm.sales_funnel.deal_repository import DealRepository
from modules.crm.sales_funnel.models import PipelineType


class CRMHomeWidget(QWidget):
    """
    Главный виджет раздела CRM
    
    Отображает папки с пиктограммами для навигации по подразделам.
    """
    
    folder_clicked = pyqtSignal(str)  # Сигнал при клике на папку
    counts_update_requested = pyqtSignal(object)  # Сигнал для обновления счетчиков (filters: tuple)
    
    def __init__(self, tender_repo=None, user_id: int = 1, bids_widget=None, main_window=None, search_params_cache=None, parent=None):
        """
        Инициализация виджета
        
        Args:
            tender_repo: Репозиторий закупок (для подменю)
            user_id: ID пользователя
            bids_widget: Виджет закупок для загрузки тендеров
            main_window: Главное окно приложения
            search_params_cache: Кэш параметров поиска (из BidsWidget для синхронизации)
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.folders: Dict[str, Dict] = {}
        self.folder_cards: Dict[str, FolderCard] = {}
        self._selected_folder_id: Optional[str] = None
        self.purchases_submenu: Optional[PurchasesSubmenuWidget] = None
        self.tender_repo = tender_repo
        self.user_id = user_id
        self.bids_widget = bids_widget
        self.main_window = main_window
        self.search_params_cache = search_params_cache
        self.deal_repo: Optional[DealRepository] = None
        self._sales_funnel_timer: Optional[QTimer] = None
        self.init_ui()
        self.load_folders()
        
        # Инициализируем репозиторий сделок для локального пересчета счетчиков воронок
        if self.tender_repo and hasattr(self.tender_repo, 'db_manager'):
            try:
                self.deal_repo = DealRepository(self.tender_repo.db_manager)
                logger.info("DealRepository инициализирован в CRMHomeWidget для подсчета сделок воронок")
                self.update_sales_funnel_counts()
                self._start_sales_funnel_counter_timer()
            except Exception as exc:
                logger.error(f"Не удалось инициализировать DealRepository в CRMHomeWidget: {exc}", exc_info=True)
    
    def init_ui(self):
        """Инициализация интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Заголовок
        header = QLabel("📁 Разделы CRM")
        apply_label_style(header, 'h1')
        header.setStyleSheet(f"color: {COLORS['primary']}; margin-bottom: {SIZES['padding_large']}px;")
        main_layout.addWidget(header)
        
        # Область прокрутки для папок
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: {COLORS['secondary']};
            }}
        """)
        
        # Контейнер для папок с grid layout
        folders_container = QWidget()
        folders_container_layout = QVBoxLayout(folders_container)
        folders_container_layout.setContentsMargins(10, 10, 10, 10)
        folders_container_layout.setSpacing(20)
        
        # Градиентный фон за карточками
        folders_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #fbfdff,
                    stop:0.45 #f4f7ff,
                    stop:0.55 #eef3ff,
                    stop:1 #e8efff
                );
                border: none;
            }
        """)
        
        # Grid layout для папок
        self.folders_layout = QGridLayout()
        self.folders_layout.setSpacing(20)
        self.folders_layout.setContentsMargins(0, 0, 0, 0)
        folders_container_layout.addLayout(self.folders_layout)
        
        # Сохраняем ссылку на layout контейнера для добавления настроек
        self.folders_container_layout = folders_container_layout
        
        scroll_area.setWidget(folders_container)
        
        # Создаем StackedWidget для переключения между главным меню и подменю
        self.stacked = QStackedWidget()
        self.stacked.addWidget(scroll_area)  # Главное меню (индекс 0)
        
        # Создаем сервис для подсчета закупок
        from modules.crm.purchases_counts_service import PurchasesCountsService
        self.counts_service = None
        if self.tender_repo:
            self.counts_service = PurchasesCountsService(self.tender_repo, self.user_id)
        
        # Используем переданный кэш или создаем новый (для обратной совместимости)
        if not self.search_params_cache:
            from modules.bids.search_params_cache import SearchParamsCache
            self.search_params_cache = SearchParamsCache()
            logger.warning("SearchParamsCache не передан в CRMHomeWidget, создан новый экземпляр")
        
        # Создаем подменю для закупок (используем тот же кэш для синхронизации настроек)
        self.purchases_submenu = PurchasesSubmenuWidget(
            counts_service=self.counts_service,
            tender_repo=self.tender_repo,
            user_id=self.user_id,
            search_params_cache=self.search_params_cache
        )
        self.purchases_submenu.submenu_item_clicked.connect(self.on_submenu_item_clicked)
        self.stacked.addWidget(self.purchases_submenu)  # Подменю закупок (индекс 1)
        
        # Создаем подменю для воронок продаж
        from modules.crm.sales_funnel.submenu_widget import SalesFunnelSubmenuWidget
        self.sales_funnel_submenu = SalesFunnelSubmenuWidget(self)
        self.sales_funnel_submenu.submenu_item_clicked.connect(self.on_submenu_item_clicked)
        self.stacked.addWidget(self.sales_funnel_submenu)  # Подменю воронок продаж (индекс 2)
        
        # Подключаем сигнал обновления счетчиков
        self.counts_update_requested.connect(self._on_counts_update_requested)
        
        main_layout.addWidget(self.stacked)
    
    def _on_counts_update_requested(self, filters):
        """Обработка запроса на обновление счетчиков"""
        if self.purchases_submenu and self.counts_service:
            # filters - это tuple (category_id, user_okpd_codes, user_stop_words, region_id)
            if isinstance(filters, tuple) and len(filters) >= 3:
                category_id = filters[0] if len(filters) > 0 else None
                user_okpd_codes = filters[1] if len(filters) > 1 else None
                user_stop_words = filters[2] if len(filters) > 2 else None
                region_id = filters[3] if len(filters) > 3 else None
                counts = self.counts_service.get_counts(
                    category_id=category_id,
                    user_okpd_codes=user_okpd_codes,
                    user_stop_words=user_stop_words,
                    region_id=region_id
                )
                self.purchases_submenu.update_counts(counts)
            else:
                # Обратная совместимость: если передано только category_id
                category_id = filters if isinstance(filters, (int, type(None))) else None
                counts = self.counts_service.get_counts(category_id=category_id)
                self.purchases_submenu.update_counts(counts)
    
    def update_sales_funnel_counts(self) -> None:
        """
        Локальный пересчет количества сделок для воронок продаж.
        
        Обновляет:
        - счетчик на основной папке "Воронка продаж"
        - счетчики в подменю воронок (участие, материалы, субподряд).
        """
        if not self.deal_repo:
            return
        
        try:
            total_count = 0
            counts_by_pipeline: Dict[PipelineType, int] = {}
            
            for pipeline_type in PipelineType:
                deals = self.deal_repo.get_deals(pipeline_type, self.user_id)
                count = len(deals)
                counts_by_pipeline[pipeline_type] = count
                total_count += count
            
            # Обновляем основную папку "Воронка продаж"
            sales_funnel_card = self.folder_cards.get('sales_funnel')
            if sales_funnel_card:
                sales_funnel_card.update_count(total_count)
            
            # Обновляем подменю воронок продаж
            if hasattr(self, 'sales_funnel_submenu') and self.sales_funnel_submenu:
                self.sales_funnel_submenu.update_counts(counts_by_pipeline)
            
            logger.info(
                "Обновлены счетчики воронок продаж: total={}, participation={}, "
                "materials={}, subcontracting={}",
                total_count,
                counts_by_pipeline.get(PipelineType.PARTICIPATION, 0),
                counts_by_pipeline.get(PipelineType.MATERIALS_SUPPLY, 0),
                counts_by_pipeline.get(PipelineType.SUBCONTRACTING, 0),
            )
        except Exception as exc:
            logger.error(f"Ошибка при обновлении счетчиков воронок продаж: {exc}", exc_info=True)
    
    def _start_sales_funnel_counter_timer(self) -> None:
        """
        Запускает периодический пересчет счетчиков воронок продаж.
        
        Используется для автоматического обновления при изменении сделок.
        """
        if not self.deal_repo:
            return
        
        if self._sales_funnel_timer:
            return
        
        self._sales_funnel_timer = QTimer(self)
        # Интервал можно подстроить при необходимости
        self._sales_funnel_timer.setInterval(5000)
        self._sales_funnel_timer.timeout.connect(self.update_sales_funnel_counts)
        self._sales_funnel_timer.start()
    
    def load_folders(self):
        """Загрузка структуры папок"""
        # Определяем структуру папок согласно документации
        # Пути к иконкам (gif с приоритетом, fallback png/эмодзи)
        procurement_icon_gif = Path(__file__).parent.parent.parent / 'img' / 'crm_menu' / 'purchaser.gif'
        procurement_icon_png = Path(__file__).parent.parent.parent / 'img' / 'crm_menu' / 'purchaser.png'
        procurement_icon_path = procurement_icon_gif if procurement_icon_gif.exists() else procurement_icon_png
        
        left_menu_dir = Path(__file__).parent.parent.parent / 'img' / 'left_menu'
        offer_icon = left_menu_dir / 'offer.gif'
        client_base_icon = left_menu_dir / 'customer base.gif'
        goods_icon = left_menu_dir / 'goods.gif'
        deals_icon = left_menu_dir / 'deals.gif'
        
        folders_data = [
            # Закупки
            {
                'id': 'purchases',
                'name': 'Закупки',
                'icon': '📊',  # Fallback если иконка не найдена
                'icon_path': str(procurement_icon_path) if procurement_icon_path.exists() else None,
                'description': 'Управление закупками',
                'subfolders': [
                    {'id': 'purchases_44fz_new', 'name': 'Новые закупки по 44 ФЗ', 'icon': '📋'},
                    {'id': 'purchases_223fz_new', 'name': 'Новые закупки по 223 ФЗ', 'icon': '📋'},
                    {'id': 'purchases_44fz_won', 'name': 'Разыгранные закупки по 44 ФЗ', 'icon': '🏆'},
                    {'id': 'purchases_223fz_won', 'name': 'Разыгранные закупки по 223 ФЗ', 'icon': '🏆'},
                ]
            },
            # Сделки
            {
                'id': 'deals',
                'name': 'Сделки',
                'icon': '💼',
                'icon_path': str(deals_icon) if deals_icon.exists() else None,
                'description': 'Управление сделками',
                'subfolders': [
                    {'id': 'deals_kanban', 'name': 'Канбан', 'icon': '📌'},
                ]
            },
            # Коммерческие предложения
            {
                'id': 'commercial_proposals',
                'name': 'Коммерческие предложения',
                'icon': '📄',
                'icon_path': str(offer_icon) if offer_icon.exists() else None,
                'description': 'Создание и управление КП',
            },
            # Клиентская база
            {
                'id': 'client_base',
                'name': 'Клиентская база',
                'icon': '👥',
                'icon_path': str(client_base_icon) if client_base_icon.exists() else None,
                'description': 'Управление клиентами',
                'subfolders': [
                    {'id': 'clients_customers', 'name': 'Заказчики', 'icon': '🏢'},
                    {'id': 'clients_contractors', 'name': 'Подрядчики', 'icon': '👷'},
                    {'id': 'clients_designers', 'name': 'Проектировщики', 'icon': '📐'},
                    {'id': 'clients_suppliers', 'name': 'Поставщики', 'icon': '🚚'},
                ]
            },
            # Каталог Товаров
            {
                'id': 'product_catalog',
                'name': 'Каталог Товаров',
                'icon': '📦',
                'icon_path': str(goods_icon) if goods_icon.exists() else None,
                'description': 'Управление каталогом',
                'subfolders': [
                    {'id': 'catalog_waterproofing', 'name': 'Гидроизоляция', 'icon': '💧'},
                    {'id': 'catalog_floors', 'name': 'Промышленные полы', 'icon': '🏗️'},
                    {'id': 'catalog_bridges', 'name': 'Мосты', 'icon': '🌉'},
                    {'id': 'catalog_heating', 'name': 'Отопление', 'icon': '🔥'},
                    {'id': 'catalog_computers', 'name': 'Компьютеры', 'icon': '💻'},
                ]
            },
            # Воронка продаж
            {
                'id': 'sales_funnel',
                'name': 'Воронка продаж',
                'icon': '📊',
                'icon_path': None,
                'description': 'Управление воронками продаж',
                'subfolders': [
                    {'id': 'sales_funnel_participation', 'name': 'Участвовать', 'icon': '🎯'},
                    {'id': 'sales_funnel_materials', 'name': 'Поставка материалов', 'icon': '📦'},
                    {'id': 'sales_funnel_subcontracting', 'name': 'Суб-подрядные работы', 'icon': '🔧'},
                ]
            },
        ]
        
        # Сохраняем данные о папках
        for folder_data in folders_data:
            self.folders[folder_data['id']] = folder_data
        
        # Отображаем папки в grid
        self.display_folders(folders_data)
    
    def display_folders(self, folders_data: list):
        """Отображение папок в grid layout"""
        # Очищаем существующие папки
        while self.folders_layout.count():
            item = self.folders_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Добавляем папки в grid (по 4 в ряд)
        row = 0
        col = 0
        max_cols = 4
        
        for folder_data in folders_data:
            # Для папки "Закупки" не показываем счетчик
            show_count = None if folder_data['id'] == 'purchases' else None
            
            folder_card = FolderCard(
                folder_id=folder_data['id'],
                name=folder_data['name'],
                icon=folder_data['icon'],
                description=folder_data.get('description'),
                count=show_count,  # Для закупок счетчик не показываем
                icon_path=folder_data.get('icon_path')
            )
            folder_card.clicked.connect(self.on_folder_clicked)
            self.folder_cards[folder_data['id']] = folder_card
            
            # Скрываем счетчик для папки "Закупки"
            if folder_data['id'] == 'purchases' and hasattr(folder_card, 'count_label'):
                folder_card.count_label.setVisible(False)
            
            self.folders_layout.addWidget(folder_card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def on_folder_clicked(self, folder_id: str):
        """Обработка клика на папку"""
        logger.info(f"Клик на папку: {folder_id}")
        
        # Если кликнули на "Закупки", показываем подменю
        if folder_id == 'purchases':
            self.stacked.setCurrentIndex(1)  # Переключаемся на подменю закупок
            return
        
        # Если кликнули на "Воронка продаж", показываем подменю
        if folder_id == 'sales_funnel':
            self.stacked.setCurrentIndex(2)  # Переключаемся на подменю воронок продаж
            return
        
        # Обновляем выделение: снимаем предыдущее, выделяем текущее
        if self._selected_folder_id and self._selected_folder_id in self.folder_cards:
            self.folder_cards[self._selected_folder_id].set_selected(False)
        self._selected_folder_id = folder_id
        if folder_id in self.folder_cards:
            self.folder_cards[folder_id].set_selected(True)
        # Пробрасываем событие дальше
        self.folder_clicked.emit(folder_id)
    
    def on_submenu_item_clicked(self, item_id: str):
        """Обработка клика на элемент подменю"""
        if item_id == 'back_to_crm':
            # Возвращаемся к главному меню
            self.stacked.setCurrentIndex(0)
        elif item_id.startswith('sales_funnel_'):
            # Клик на элемент воронки продаж - пробрасываем событие
            self.folder_clicked.emit(item_id)
        else:
            # Пробрасываем событие дальше для обработки в MainWindow
            self.folder_clicked.emit(item_id)
    
    def get_folder_data(self, folder_id: str) -> Optional[Dict]:
        """Получение данных о папке"""
        return self.folders.get(folder_id)
    
    def handle_show_tenders(self):
        """Обработка нажатия кнопки 'Показать тендеры' из настроек"""
        if not self.bids_widget:
            logger.warning("BidsWidget не передан в CRMHomeWidget")
            return
        
        if not self.main_window:
            logger.warning("MainWindow не передан в CRMHomeWidget")
            return
        
        # Ищем BidsWidget в стеке
        bids_index = None
        for i in range(self.main_window.stacked.count()):
            if self.main_window.stacked.widget(i) == self.bids_widget:
                bids_index = i
                break
        
        # Если BidsWidget не в стеке, добавляем его
        if bids_index is None:
            bids_index = self.main_window.stacked.count()
            self.main_window.stacked.addWidget(self.bids_widget)
        
        # Переключаемся на BidsWidget
        self.main_window.stacked.setCurrentIndex(bids_index)
        
        # Обновляем кнопку в меню - переключаемся на CRM
        if hasattr(self.main_window, 'crm_index') and self.main_window.crm_index is not None:
            if hasattr(self.main_window, 'buttons') and self.main_window.buttons:
                self.main_window.buttons[self.main_window.crm_index].setChecked(True)
        
        # Вызываем метод загрузки тендеров в BidsWidget
        if hasattr(self.bids_widget, 'handle_show_tenders'):
            self.bids_widget.handle_show_tenders()
        else:
            logger.warning("BidsWidget не имеет метода handle_show_tenders")

