"""
Виджет для управления закупками (44ФЗ и 223ФЗ)

Виджет предоставляет интерфейс для:
- Управления новыми закупками 44ФЗ и 223ФЗ через канбан-доски
- Просмотра разыгранных закупок
- Настройки параметров закупок
- Отслеживания закупок в работе
"""

from PyQt5.QtWidgets import QWidget
from typing import Optional
from pathlib import Path
from loguru import logger


# Импортируем модули для обработки процессов и загрузки тендеров
from modules.bids.tender_loader import TenderLoader
from modules.bids.document_processor import DocumentProcessor
from modules.bids.search_params_cache import SearchParamsCache

# Импортируем новые модули для рефакторинга
from modules.bids.bids_tender_loader import BidsTenderLoader
from modules.bids.bids_document_analyzer import BidsDocumentAnalyzer
from modules.bids.bids_cache_manager import BidsCacheManager
from modules.bids.bids_database_manager import BidsDatabaseManager
from modules.bids.bids_tabs_manager import BidsTabsManager
from modules.bids.bids_ui_builder import BidsUIBuilder

# Импортируем репозиторий для работы с закупками
from services.tender_repository import TenderRepository
from services.tender_match_repository import TenderMatchRepository
from services.document_search_service import DocumentSearchService
from core.tender_database import TenderDatabaseManager
from config.settings import config
from core.database import DatabaseManager

# DOCUMENT_DOWNLOAD_DIR - путь к директории для скачивания документов из ЕИС
# Настраивается через переменную окружения DOCUMENT_DOWNLOAD_DIR в .env файле
# Пример: DOCUMENT_DOWNLOAD_DIR=C:\Projects\Documents\Tenders


class BidsWidget(QWidget):
    """
    Виджет для управления закупками
    
    Содержит вкладки для различных типов закупок и их статусов.
    """
    
    def __init__(
        self,
        product_db_manager: Optional[DatabaseManager] = None,
        tender_repository: Optional[TenderRepository] = None,
        tender_match_repository: Optional[TenderMatchRepository] = None,
        document_search_service: Optional[DocumentSearchService] = None,
    ):
        """
        Инициализация виджета закупок
        
        Args:
            product_db_manager: Менеджер БД продуктов (для обратной совместимости)
            tender_repository: Репозиторий закупок (опционально, создается через DI если не передан)
            tender_match_repository: Репозиторий результатов поиска (опционально)
            document_search_service: Сервис поиска документов (опционально)
        """
        super().__init__()
        
        # Внедрение зависимостей через DI контейнер или переданные параметры
        from core.dependency_injection import container
        
        # Инициализация подключения к БД tender_monitor (обязательно)
        if not config.tender_database:
            error_msg = "Конфигурация БД tender_monitor не задана. Проверьте переменные окружения в .env файле."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Используем переданные зависимости или создаем через контейнер
            if tender_repository:
                self.tender_repo = tender_repository
                self.tender_db_manager = tender_repository.db_manager if hasattr(tender_repository, 'db_manager') else None
            else:
                self.tender_db_manager = container.get_tender_database_manager()
                self.tender_repo = container.get_tender_repository()
            
            if tender_match_repository:
                self.tender_match_repo = tender_match_repository
            else:
                self.tender_match_repo = container.get_tender_match_repository()
            # Алиас для обратной совместимости с новым именем атрибута
            self.tender_match_repository = self.tender_match_repo
            
            logger.info("Подключение к БД tender_monitor установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к БД tender_monitor: {e}")
            raise  # Пробрасываем ошибку, так как подключение обязательно
        
        # Временный ID пользователя (позже будет из системы авторизации)
        self.current_user_id = 1
        self.product_db_manager = product_db_manager
        
        # Инициализация сервиса поиска документов
        if document_search_service:
            self.document_search_service = document_search_service
        elif self.product_db_manager:
            # Получаем путь к директории для скачивания документов из .env
            download_dir = Path(config.document_download_dir) if config.document_download_dir else Path.home() / "Downloads" / "ЕИС_Документация"
            self.document_search_service = DocumentSearchService(
                self.product_db_manager,
                download_dir,
                unrar_path=config.unrar_tool,
                winrar_path=config.winrar_path,
            )
            logger.info("Сервис поиска по документации инициализирован")
        else:
            # Пытаемся получить через контейнер
            try:
                self.document_search_service = container.get_document_search_service()
                logger.info("Сервис поиска по документации получен через DI контейнер")
            except Exception as e:
                logger.warning(f"Сервис поиска документации недоступен: {e}")
                self.document_search_service = None
        
        # Инициализируем кэш параметров поиска (до загрузчика тендеров, т.к. он его использует)
        self.search_params_cache = SearchParamsCache()
        
        # Инициализируем загрузчик тендеров
        tender_loader_base = TenderLoader(
            tender_repo=self.tender_repo,
            document_search_service=self.document_search_service,
            cache=self.search_params_cache
        )
        self.tender_loader = BidsTenderLoader(tender_loader_base)
        
        # Инициализируем процессор документов
        document_processor_base = DocumentProcessor(user_id=self.current_user_id)
        self.document_analyzer = BidsDocumentAnalyzer(document_processor_base)
        
        # Инициализируем менеджеры
        self.cache_manager = BidsCacheManager(self.search_params_cache)
        self.db_manager = BidsDatabaseManager(
            self.tender_db_manager,
            self.tender_repo,
            self.tender_match_repo,
            self.current_user_id,
            self.search_params_cache
        )
        
        # Создаем простой UI без вкладок - только список карточек
        from PyQt5.QtWidgets import QVBoxLayout, QLabel, QFrame
        from modules.bids.tender_list_widget import TenderListWidget
        from modules.styles.general_styles import apply_label_style, apply_frame_style
        
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок раздела с кнопками
        header_frame = QFrame()
        apply_frame_style(header_frame, 'content')
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Заголовок и кнопки в одной строке
        from PyQt5.QtWidgets import QHBoxLayout, QPushButton
        from modules.styles.general_styles import apply_button_style
        
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QLabel("📈 Закупки")
        apply_label_style(self.title_label, 'h1')
        header_row.addWidget(self.title_label)
        
        header_row.addStretch()
        
        # Кнопка анализа документации для выбранных закупок
        self.analyze_button = QPushButton("📄 Анализ выбранных")
        apply_button_style(self.analyze_button, 'primary')
        self.analyze_button.setToolTip("Запустить анализ документации для выбранных закупок")
        self.analyze_button.setEnabled(False)
        header_row.addWidget(self.analyze_button)
        
        # Кнопка анализа всех закупок
        self.analyze_all_button = QPushButton("📊 Анализировать все")
        apply_button_style(self.analyze_all_button, 'secondary')
        self.analyze_all_button.setToolTip("Запустить анализ документации для всех закупок в текущем разделе (приоритетные обрабатываются первыми)")
        header_row.addWidget(self.analyze_all_button)
        
        # Кнопка обновления ленты
        self.refresh_button = QPushButton("🔄 Обновить ленту")
        apply_button_style(self.refresh_button, 'outline')
        self.refresh_button.setToolTip("Обновить статусы обработки документов для всех закупок")
        header_row.addWidget(self.refresh_button)
        
        header_layout.addLayout(header_row)
        main_layout.addWidget(header_frame)
        
        # Подключаем обработчики кнопок
        self.analyze_button.clicked.connect(self.handle_analyze_selected_tenders)
        self.analyze_all_button.clicked.connect(self.handle_analyze_all_tenders)
        self.refresh_button.clicked.connect(self.refresh_current_feed)
        
        # Создаем виджеты для каждого раздела (но показываем только нужный)
        self.tenders_44fz_widget = TenderListWidget(
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repo,
        )
        self.tenders_223fz_widget = TenderListWidget(
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repo,
        )
        self.won_tenders_44fz_widget = TenderListWidget(
            parent=self,
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repo,
        )
        self.won_tenders_223fz_widget = TenderListWidget(
            parent=self,
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repo,
        )
        self.commission_tenders_44fz_widget = TenderListWidget(
            parent=self,
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repo,
        )
        
        # Текущий активный виджет (показывается в layout)
        self.current_widget = None
        self.current_section_id = None
        self.current_section_title = None
        
        # Подключаем обработчик изменения выбора закупок
        if hasattr(self.tenders_44fz_widget, 'selection_changed'):
            self.tenders_44fz_widget.selection_changed.connect(self.on_tender_selection_changed)
        if hasattr(self.tenders_223fz_widget, 'selection_changed'):
            self.tenders_223fz_widget.selection_changed.connect(self.on_tender_selection_changed)
        if hasattr(self.won_tenders_44fz_widget, 'selection_changed'):
            self.won_tenders_44fz_widget.selection_changed.connect(self.on_tender_selection_changed)
        if hasattr(self.won_tenders_223fz_widget, 'selection_changed'):
            self.won_tenders_223fz_widget.selection_changed.connect(self.on_tender_selection_changed)
        if hasattr(self.commission_tenders_44fz_widget, 'selection_changed'):
            self.commission_tenders_44fz_widget.selection_changed.connect(self.on_tender_selection_changed)
        
        # Инициализируем менеджер загрузки (без вкладок)
        self.tender_loader_manager = BidsTenderLoader(self.tender_loader.tender_loader)
    
    def show_section(self, section_id: str):
        """
        Показ нужного раздела закупок
        
        Args:
            section_id: ID раздела ('purchases_44fz_new', 'purchases_44fz_won', и т.д.)
        """
        from PyQt5.QtWidgets import QVBoxLayout
        
        # Определяем какой виджет показывать
        widget_map = {
            'purchases_44fz_new': (self.tenders_44fz_widget, "Новые закупки по 44 ФЗ"),
            'purchases_223fz_new': (self.tenders_223fz_widget, "Новые закупки по 223 ФЗ"),
            'purchases_44fz_won': (self.won_tenders_44fz_widget, "Разыгранные закупки по 44 ФЗ"),
            'purchases_223fz_won': (self.won_tenders_223fz_widget, "Разыгранные закупки по 223 ФЗ"),
            'purchases_44fz_commission': (self.commission_tenders_44fz_widget, "Работа комиссии 44 ФЗ"),
        }
        
        if section_id not in widget_map:
            logger.warning(f"Неизвестный раздел: {section_id}")
            return
        
        target_widget, title = widget_map[section_id]
        
        # Сохраняем текущий раздел для использования в обработчиках кнопок
        self.current_section_id = section_id
        self.current_section_title = title
        
        # Убираем текущий виджет из layout
        if self.current_widget:
            layout = self.layout()
            if layout:
                layout.removeWidget(self.current_widget)
                self.current_widget.hide()
        
        # Показываем нужный виджет
        self.current_widget = target_widget
        self.title_label.setText(f"📈 {title}")
        
        layout = self.layout()
        if layout:
            layout.addWidget(self.current_widget)
            self.current_widget.show()
        
        # Загружаем данные если еще не загружены или если force=True
        # force=True означает, что нужно перезагрузить данные (например, после изменения фильтров)
        force_reload = getattr(self, '_force_reload', False)
        if not getattr(target_widget, '_loaded', False) or force_reload:
            self._load_section_data(section_id, target_widget)
            # Сбрасываем флаг после загрузки
            if force_reload:
                self._force_reload = False
    
    def _load_section_data(self, section_id: str, widget):
        """Загрузка данных для раздела"""
        # Получаем категорию из кэша для логирования
        category_id = self.search_params_cache.get_category_id()
        logger.info(f"Загрузка данных для раздела {section_id}, категория из кэша: {category_id}")
        category_filter_combo = None  # Будет None, т.к. настройки в подменю
        
        if section_id == 'purchases_44fz_new':
            self.tender_loader_manager.load_tenders_44fz(
                widget=widget,
                user_id=self.current_user_id,
                category_filter_combo=category_filter_combo,
                force=False,
                parent_widget=self
            )
        elif section_id == 'purchases_223fz_new':
            self.tender_loader_manager.load_tenders_223fz(
                widget=widget,
                user_id=self.current_user_id,
                category_filter_combo=category_filter_combo,
                force=False,
                parent_widget=self
            )
        elif section_id == 'purchases_44fz_won':
            self.tender_loader_manager.load_won_tenders_44fz(
                widget=widget,
                user_id=self.current_user_id,
                category_filter_combo=category_filter_combo,
                force=False,
                parent_widget=self
            )
        elif section_id == 'purchases_223fz_won':
            self.tender_loader_manager.load_won_tenders_223fz(
                widget=widget,
                user_id=self.current_user_id,
                category_filter_combo=category_filter_combo,
                force=False,
                parent_widget=self
            )
        elif section_id == 'purchases_44fz_commission':
            self.tender_loader_manager.load_commission_tenders_44fz(
                widget=widget,
                user_id=self.current_user_id,
                category_filter_combo=category_filter_combo,
                force=False,
                parent_widget=self
            )
    
    def on_tender_selection_changed(self):
        """Обработка изменения выбора закупок"""
        # Активируем кнопку "Анализ выбранных" если есть выбранные закупки
        if self.current_widget and hasattr(self.current_widget, 'get_selected_tenders'):
            selected = self.current_widget.get_selected_tenders()
            self.analyze_button.setEnabled(len(selected) > 0)
        else:
            self.analyze_button.setEnabled(False)
    
    def handle_analyze_selected_tenders(self):
        """Обработка нажатия кнопки 'Анализ выбранных'"""
        if not self.current_widget:
            return
        
        # Получаем выбранные закупки из текущего виджета
        selected = []
        if hasattr(self.current_widget, 'get_selected_tenders'):
            selected = self.current_widget.get_selected_tenders()
        
        if not selected:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы одну закупку для анализа")
            return
        
        # Определяем тип реестра и закупок по текущему разделу
        registry_type = None
        tender_type = 'new'
        
        if self.current_section_id == 'purchases_44fz_new':
            registry_type = '44fz'
            tender_type = 'new'
        elif self.current_section_id == 'purchases_223fz_new':
            registry_type = '223fz'
            tender_type = 'new'
        elif self.current_section_id == 'purchases_44fz_won':
            registry_type = '44fz'
            tender_type = 'won'
        elif self.current_section_id == 'purchases_223fz_won':
            registry_type = '223fz'
            tender_type = 'won'
        elif self.current_section_id == 'purchases_44fz_commission':
            registry_type = '44fz'
            tender_type = 'commission'
        
        # Определяем правильные виджеты для передачи в анализатор
        # Анализатор использует current_tab_text для определения откуда брать выбранные закупки
        # Поэтому передаем текущий виджет в соответствующее поле
        won_tenders_44fz_widget = None
        won_tenders_223fz_widget = None
        commission_tenders_44fz_widget = None
        
        if registry_type == '44fz':
            if tender_type == 'new':
                tenders_44fz_widget = self.current_widget
                tenders_223fz_widget = self.tenders_223fz_widget
            elif tender_type == 'won':
                tenders_44fz_widget = self.tenders_44fz_widget
                tenders_223fz_widget = self.tenders_223fz_widget
                won_tenders_44fz_widget = self.current_widget
            else:  # commission
                tenders_44fz_widget = self.tenders_44fz_widget
                tenders_223fz_widget = self.tenders_223fz_widget
                commission_tenders_44fz_widget = self.current_widget
        else:  # 223fz
            if tender_type == 'new':
                tenders_44fz_widget = self.tenders_44fz_widget
                tenders_223fz_widget = self.current_widget
            elif tender_type == 'won':
                tenders_44fz_widget = self.tenders_44fz_widget
                tenders_223fz_widget = self.tenders_223fz_widget
                won_tenders_223fz_widget = self.current_widget
        
        # Вызываем метод анализатора
        self.document_analyzer.handle_analyze_selected_tenders(
            tenders_44fz_widget=tenders_44fz_widget,
            tenders_223fz_widget=tenders_223fz_widget,
            won_tenders_44fz_widget=won_tenders_44fz_widget,
            won_tenders_223fz_widget=won_tenders_223fz_widget,
            commission_tenders_44fz_widget=commission_tenders_44fz_widget,
            current_tab_text=self.current_section_title or "",
            parent_widget=self
        )
    
    def handle_analyze_all_tenders(self):
        """Обработка нажатия кнопки 'Анализировать все'"""
        if not self.current_widget:
            return
        
        # Определяем тип реестра и закупок по текущему разделу
        registry_type = None
        tender_type = 'new'
        current_tab_text = ""
        
        if self.current_section_id == 'purchases_44fz_new':
            registry_type = '44fz'
            tender_type = 'new'
            current_tab_text = "Новые закупки 44ФЗ"
        elif self.current_section_id == 'purchases_223fz_new':
            registry_type = '223fz'
            tender_type = 'new'
            current_tab_text = "Новые закупки 223ФЗ"
        elif self.current_section_id == 'purchases_44fz_won':
            registry_type = '44fz'
            tender_type = 'won'
            current_tab_text = "Разыгранные закупки 44ФЗ"
        elif self.current_section_id == 'purchases_223fz_won':
            registry_type = '223fz'
            tender_type = 'won'
            current_tab_text = "Разыгранные закупки 223ФЗ"
        elif self.current_section_id == 'purchases_44fz_commission':
            registry_type = '44fz'
            tender_type = 'commission'
            current_tab_text = "Работа комиссии 44 ФЗ"
        
        # Вызываем метод анализатора
        self.document_analyzer.handle_analyze_all_tenders(
            tenders_44fz_widget=self.tenders_44fz_widget,
            tenders_223fz_widget=self.tenders_223fz_widget,
            won_tenders_44fz_widget=self.won_tenders_44fz_widget,
            won_tenders_223fz_widget=self.won_tenders_223fz_widget,
            commission_tenders_44fz_widget=self.commission_tenders_44fz_widget,
            current_tab_text=current_tab_text,
            parent_widget=self
        )
    
    def refresh_current_feed(self):
        """Обновление статусов обработки документов для текущего раздела"""
        if not self.current_widget:
            return
        
        # Перезагружаем данные для текущего раздела
        if self.current_section_id:
            self._load_section_data(self.current_section_id, self.current_widget)
    
    def _handle_db_reconnection(self) -> None:
        """Обработка переподключения к БД с восстановлением параметров"""
        self.db_manager.handle_db_reconnection(
            self,
            self.cache_manager,
            getattr(self, 'settings_tab', None)
        )
        # Обновляем ссылки на репозитории после переподключения
        self.tender_repo = self.db_manager.tender_repo
        self.tender_match_repo = self.db_manager.tender_match_repo
        self.tender_match_repository = self.tender_match_repo
