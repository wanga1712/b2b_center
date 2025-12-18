"""
Вкладка настроек для виджета закупок

Содержит UI и логику для:
- Выбора кодов ОКПД
- Управления категориями ОКПД
- Управления стоп-словами
- Фильтрации по региону и категории
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QLineEdit, QPushButton, QListWidget, QScrollArea,
    QComboBox
)
from PyQt5.QtCore import Qt, QTimer
import html
from typing import Optional
from loguru import logger

from modules.styles.general_styles import (
    apply_label_style, apply_frame_style, apply_input_style, apply_button_style,
    apply_scroll_area_style, apply_list_widget_style, apply_text_style_light_italic
)

from modules.bids.settings_okpd_manager import OKPDManager
from modules.bids.settings_stop_words_manager import StopWordsManager
from modules.bids.settings_document_stop_phrases_manager import DocumentStopPhrasesManager
from modules.bids.settings_categories_manager import CategoriesManager
from modules.bids.search_params_cache import SearchParamsCache
from services.tender_repository import TenderRepository
from core.exceptions import DatabaseConnectionError, DatabaseQueryError


class BidsSettingsTab(QWidget):
    """
    Вкладка настроек для виджета закупок
    
    Управляет всеми настройками: ОКПД, категории, стоп-слова, регионы
    """
    
    def __init__(
        self,
        tender_repo: TenderRepository,
        user_id: int,
        search_params_cache: SearchParamsCache,
        parent_widget: Optional[QWidget] = None
    ):
        """
        Инициализация вкладки настроек
        
        Args:
            tender_repo: Репозиторий закупок
            user_id: ID пользователя
            search_params_cache: Кэш параметров поиска
            parent_widget: Родительский виджет (для обратных вызовов)
        """
        super().__init__()
        self._is_initializing = True
        self._restoring_from_cache = False
        self.tender_repo = tender_repo
        self.user_id = user_id
        self.search_params_cache = search_params_cache
        self.parent_widget = parent_widget
        
        # Инициализируем менеджеры
        self.okpd_manager = OKPDManager(self.tender_repo, self.user_id)
        self.stop_words_manager = StopWordsManager(self.tender_repo, self.user_id)
        self.document_stop_phrases_manager = DocumentStopPhrasesManager(self.tender_repo, self.user_id)
        self.categories_manager = CategoriesManager(self.tender_repo, self.user_id)
        
        self.init_ui()
        self._init_settings_data()
        self._is_initializing = False
    
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        # Создаем контейнер с прокруткой для всей вкладки
        scroll_widget = QWidget()
        settings_layout = QVBoxLayout(scroll_widget)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(15)
        
        # Создаем ScrollArea для прокрутки всего контента
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        apply_scroll_area_style(scroll_area, 'subtle')
        
        tab_layout = QVBoxLayout(self)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)
        tab_layout.addWidget(scroll_area)
        
        # Заголовок
        settings_label = QLabel("Настройки закупок")
        apply_label_style(settings_label, 'h2')
        settings_layout.addWidget(settings_label)
        
        # Раздел фильтрации по категории
        self._create_category_filter_section(settings_layout)
        
        # Раздел выбора ОКПД
        self._create_okpd_section(settings_layout)
        
        # Раздел управления категориями ОКПД
        self._create_categories_section(settings_layout)
        
        # Раздел добавленных ОКПД
        self._create_added_okpd_section(settings_layout)
        
        # Раздел стоп-слов
        self._create_stop_words_section(settings_layout)

        # Раздел стоп-фраз анализа документации
        self._create_document_stop_phrases_section(settings_layout)
        
        # Кнопка показать тендеры
        self._create_show_tenders_section(settings_layout)
        
        # Загружаем регионы после создания всех элементов
        self._init_regions()
    
    def _create_category_filter_section(self, parent_layout: QVBoxLayout):
        """Создание раздела фильтрации по категории"""
        filter_category_frame = QFrame()
        apply_frame_style(filter_category_frame, 'content')
        filter_category_layout = QVBoxLayout(filter_category_frame)
        filter_category_layout.setContentsMargins(15, 15, 15, 15)
        filter_category_layout.setSpacing(10)
        
        filter_category_title = QLabel("Фильтрация закупок по категории")
        apply_label_style(filter_category_title, 'h3')
        filter_category_layout.addWidget(filter_category_title)
        
        filter_category_info = QLabel(
            "Выберите категорию ОКПД для фильтрации закупок. "
            "Будут показаны только закупки с ОКПД кодами из выбранной категории."
        )
        apply_label_style(filter_category_info, 'small')
        apply_text_style_light_italic(filter_category_info)
        filter_category_info.setWordWrap(True)
        filter_category_layout.addWidget(filter_category_info)
        
        category_filter_layout = QHBoxLayout()
        category_filter_layout.setSpacing(10)
        
        category_filter_label = QLabel("Категория:")
        apply_label_style(category_filter_label, 'normal')
        category_filter_label.setMinimumWidth(80)
        category_filter_layout.addWidget(category_filter_label)
        
        self.category_filter_combo = QComboBox()
        self.category_filter_combo.setMinimumWidth(300)
        apply_input_style(self.category_filter_combo)
        self.category_filter_combo.addItem("Все категории", None)
        self.category_filter_combo.currentIndexChanged.connect(self.on_category_filter_changed)
        category_filter_layout.addWidget(self.category_filter_combo)
        
        category_filter_layout.addStretch()
        filter_category_layout.addLayout(category_filter_layout)
        
        parent_layout.addWidget(filter_category_frame)
    
    def _create_okpd_section(self, parent_layout: QVBoxLayout):
        """Создание раздела выбора ОКПД"""
        okpd_frame = QFrame()
        apply_frame_style(okpd_frame, 'content')
        okpd_layout = QVBoxLayout(okpd_frame)
        okpd_layout.setContentsMargins(15, 15, 15, 15)
        okpd_layout.setSpacing(10)
        
        okpd_title = QLabel("Выбор кодов ОКПД")
        apply_label_style(okpd_title, 'h3')
        okpd_layout.addWidget(okpd_title)
        
        # Фильтр по региону
        region_layout = QHBoxLayout()
        region_layout.setSpacing(10)
        
        region_label = QLabel("Регион:")
        apply_label_style(region_label, 'normal')
        region_label.setMinimumWidth(60)
        region_layout.addWidget(region_label)
        
        self.region_combo = QComboBox()
        self.region_combo.setMinimumWidth(300)
        apply_input_style(self.region_combo)
        region_layout.addWidget(self.region_combo)
        
        region_layout.addStretch()
        okpd_layout.addLayout(region_layout)
        
        # Поле поиска ОКПД
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        
        self.okpd_search_input = QLineEdit()
        self.okpd_search_input.setPlaceholderText("Введите код ОКПД или название для поиска...")
        apply_input_style(self.okpd_search_input)
        self.okpd_search_input.textChanged.connect(self.on_okpd_search_changed)
        search_layout.addWidget(self.okpd_search_input)
        
        btn_add_okpd = QPushButton("Добавить")
        apply_button_style(btn_add_okpd, 'primary')
        btn_add_okpd.clicked.connect(self.handle_add_okpd)
        search_layout.addWidget(btn_add_okpd)
        
        okpd_layout.addLayout(search_layout)
        
        # Список найденных ОКПД
        results_label = QLabel("Доступные коды ОКПД для добавления:")
        apply_label_style(results_label, 'normal')
        okpd_layout.addWidget(results_label)
        
        self.okpd_results_list = QListWidget()
        self.okpd_results_list.setMinimumHeight(300)
        self.okpd_results_list.setMaximumHeight(400)
        apply_list_widget_style(self.okpd_results_list)
        okpd_layout.addWidget(self.okpd_results_list)
        
        parent_layout.addWidget(okpd_frame)
    
    def _create_categories_section(self, parent_layout: QVBoxLayout):
        """Создание раздела управления категориями ОКПД"""
        categories_frame = QFrame()
        apply_frame_style(categories_frame, 'content')
        categories_layout = QVBoxLayout(categories_frame)
        categories_layout.setContentsMargins(15, 15, 15, 15)
        categories_layout.setSpacing(10)
        
        categories_title = QLabel("Категории ОКПД")
        apply_label_style(categories_title, 'h3')
        categories_layout.addWidget(categories_title)
        
        categories_info = QLabel(
            "Создавайте категории для группировки ОКПД кодов (например: компьютеры, стройка, проекты). "
            "При выборе категории в поиске закупок будут отображаться только закупки с ОКПД кодами из этой категории."
        )
        apply_label_style(categories_info, 'small')
        apply_text_style_light_italic(categories_info)
        categories_info.setWordWrap(True)
        categories_layout.addWidget(categories_info)
        
        # Управление категориями
        category_management_layout = QHBoxLayout()
        category_management_layout.setSpacing(10)
        
        self.category_name_input = QLineEdit()
        self.category_name_input.setPlaceholderText("Название категории (например: компьютеры)")
        apply_input_style(self.category_name_input)
        category_management_layout.addWidget(self.category_name_input)
        
        btn_create_category = QPushButton("Создать категорию")
        apply_button_style(btn_create_category, 'primary')
        btn_create_category.clicked.connect(self.handle_create_category)
        category_management_layout.addWidget(btn_create_category)
        
        categories_layout.addLayout(category_management_layout)
        
        # Список категорий
        categories_list_label = QLabel("Существующие категории:")
        apply_label_style(categories_list_label, 'normal')
        categories_layout.addWidget(categories_list_label)
        
        self.categories_list = QListWidget()
        self.categories_list.setMinimumHeight(150)
        self.categories_list.setMaximumHeight(300)
        apply_list_widget_style(self.categories_list)
        categories_layout.addWidget(self.categories_list)
        
        # Кнопки управления категорией
        category_actions_layout = QHBoxLayout()
        category_actions_layout.setSpacing(10)
        
        btn_delete_category = QPushButton("Удалить категорию")
        apply_button_style(btn_delete_category, 'secondary')
        btn_delete_category.clicked.connect(self.handle_delete_category)
        category_actions_layout.addWidget(btn_delete_category)
        
        category_actions_layout.addStretch()
        categories_layout.addLayout(category_actions_layout)
        
        parent_layout.addWidget(categories_frame)
    
    def _create_added_okpd_section(self, parent_layout: QVBoxLayout):
        """Создание раздела добавленных ОКПД"""
        added_frame = QFrame()
        apply_frame_style(added_frame, 'content')
        added_layout = QVBoxLayout(added_frame)
        added_layout.setContentsMargins(15, 15, 15, 15)
        added_layout.setSpacing(10)
        
        added_title = QLabel("Добавленные коды ОКПД")
        apply_label_style(added_title, 'h3')
        added_layout.addWidget(added_title)
        
        self.added_okpd_container = QWidget()
        self.added_okpd_layout = QVBoxLayout(self.added_okpd_container)
        self.added_okpd_layout.setSpacing(8)
        self.added_okpd_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.added_okpd_container)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMaximumHeight(500)
        apply_scroll_area_style(scroll_area, 'card')
        added_layout.addWidget(scroll_area)
        
        parent_layout.addWidget(added_frame)
    
    def _create_stop_words_section(self, parent_layout: QVBoxLayout):
        """Создание раздела стоп-слов"""
        stop_words_frame = QFrame()
        apply_frame_style(stop_words_frame, 'content')
        stop_words_layout = QVBoxLayout(stop_words_frame)
        stop_words_layout.setContentsMargins(15, 15, 15, 15)
        stop_words_layout.setSpacing(10)
        
        stop_words_title = QLabel("Стоп-слова")
        apply_label_style(stop_words_title, 'h3')
        stop_words_layout.addWidget(stop_words_title)
        
        stop_words_info = QLabel(
            "Стоп-слова используются для фильтрации закупок. "
            "Закупки, содержащие стоп-слова, будут исключены из результатов."
        )
        apply_label_style(stop_words_info, 'small')
        apply_text_style_light_italic(stop_words_info)
        stop_words_info.setWordWrap(True)
        stop_words_layout.addWidget(stop_words_info)
        
        # Поле ввода новых стоп-слов
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        
        self.stop_words_input = QLineEdit()
        self.stop_words_input.setPlaceholderText("Введите стоп-слово или несколько через запятую...")
        apply_input_style(self.stop_words_input)
        input_layout.addWidget(self.stop_words_input)
        
        btn_add_stop_word = QPushButton("Добавить")
        apply_button_style(btn_add_stop_word, 'primary')
        btn_add_stop_word.clicked.connect(self.handle_add_stop_words)
        input_layout.addWidget(btn_add_stop_word)
        
        stop_words_layout.addLayout(input_layout)
        
        # Контейнер для отображения добавленных стоп-слов
        self.stop_words_container = QWidget()
        self.stop_words_layout = QVBoxLayout(self.stop_words_container)
        self.stop_words_layout.setSpacing(8)
        self.stop_words_layout.setContentsMargins(0, 0, 0, 0)
        
        stop_words_scroll = QScrollArea()
        stop_words_scroll.setWidgetResizable(True)
        stop_words_scroll.setWidget(self.stop_words_container)
        stop_words_scroll.setMinimumHeight(200)
        stop_words_scroll.setMaximumHeight(400)
        apply_scroll_area_style(stop_words_scroll, 'card')
        stop_words_layout.addWidget(stop_words_scroll)
        
        parent_layout.addWidget(stop_words_frame)

    def _create_document_stop_phrases_section(self, parent_layout: QVBoxLayout):
        """Создание раздела стоп-фраз для анализа документации."""
        stop_phrases_frame = QFrame()
        apply_frame_style(stop_phrases_frame, 'content')
        stop_phrases_layout = QVBoxLayout(stop_phrases_frame)
        stop_phrases_layout.setContentsMargins(15, 15, 15, 15)
        stop_phrases_layout.setSpacing(10)

        stop_phrases_title = QLabel("Стоп-фразы для анализа документации")
        apply_label_style(stop_phrases_title, 'h3')
        stop_phrases_layout.addWidget(stop_phrases_title)

        stop_phrases_info = QLabel(
            "Стоп-фразы используются при поиске товаров в сметах и другой "
            "документации. Если в тексте строки присутствует одна из стоп-фраз, "
            "эта строка не будет учитываться как совпадение с товаром."
        )
        apply_label_style(stop_phrases_info, 'small')
        apply_text_style_light_italic(stop_phrases_info)
        stop_phrases_info.setWordWrap(True)
        stop_phrases_layout.addWidget(stop_phrases_info)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        self.document_stop_phrases_input = QLineEdit()
        self.document_stop_phrases_input.setPlaceholderText(
            "Введите стоп-фразу или несколько через запятую..."
        )
        apply_input_style(self.document_stop_phrases_input)
        input_layout.addWidget(self.document_stop_phrases_input)

        btn_add_stop_phrase = QPushButton("Добавить")
        apply_button_style(btn_add_stop_phrase, 'primary')
        btn_add_stop_phrase.clicked.connect(self.handle_add_document_stop_phrases)
        input_layout.addWidget(btn_add_stop_phrase)

        stop_phrases_layout.addLayout(input_layout)

        self.document_stop_phrases_container = QWidget()
        self.document_stop_phrases_layout = QVBoxLayout(self.document_stop_phrases_container)
        self.document_stop_phrases_layout.setSpacing(8)
        self.document_stop_phrases_layout.setContentsMargins(0, 0, 0, 0)

        stop_phrases_scroll = QScrollArea()
        stop_phrases_scroll.setWidgetResizable(True)
        stop_phrases_scroll.setWidget(self.document_stop_phrases_container)
        stop_phrases_scroll.setMinimumHeight(150)
        stop_phrases_scroll.setMaximumHeight(350)
        apply_scroll_area_style(stop_phrases_scroll, 'card')
        stop_phrases_layout.addWidget(stop_phrases_scroll)

        parent_layout.addWidget(stop_phrases_frame)
    
    def _create_show_tenders_section(self, parent_layout: QVBoxLayout):
        """Создание раздела кнопки показать тендеры"""
        show_tenders_frame = QFrame()
        apply_frame_style(show_tenders_frame, 'content')
        show_tenders_layout = QVBoxLayout(show_tenders_frame)
        show_tenders_layout.setContentsMargins(15, 15, 15, 15)
        show_tenders_layout.setSpacing(10)
        
        show_tenders_info = QLabel(
            "После настройки фильтров нажмите кнопку ниже, "
            "чтобы загрузить закупки по выбранным критериям."
        )
        apply_label_style(show_tenders_info, 'small')
        apply_text_style_light_italic(show_tenders_info)
        show_tenders_info.setWordWrap(True)
        show_tenders_layout.addWidget(show_tenders_info)
        
        btn_show_tenders = QPushButton("🔍 Показать тендеры")
        apply_button_style(btn_show_tenders, 'primary')
        btn_show_tenders.clicked.connect(self.handle_show_tenders)
        btn_show_tenders.setMinimumHeight(50)
        show_tenders_layout.addWidget(btn_show_tenders)
        
        parent_layout.addWidget(show_tenders_frame)
    
    def _init_regions(self):
        """Инициализация регионов"""
        try:
            self.region_combo.blockSignals(True)
            self.load_regions()
            self.region_combo.blockSignals(False)
            self.region_combo.currentIndexChanged.connect(self.on_region_changed)
        except Exception as e:
            logger.error(f"Ошибка при инициализации регионов: {e}")
            if hasattr(self, 'region_combo') and self.region_combo:
                self.region_combo.blockSignals(False)
    
    def _init_settings_data(self) -> None:
        """Инициализация данных после построения интерфейса"""
        try:
            logger.info("Инициализация данных настроек (ОКПД, категории, стоп-слова, стоп-фразы документации)")
            self.load_okpd_codes()
            self.load_okpd_categories()
            self.load_user_okpd_codes()
            self.load_user_stop_words()
            self.load_document_stop_phrases()
        except Exception as e:
            logger.error(f"Ошибка при инициализации данных настроек: {e}")
    
    def load_okpd_codes(self, search_text: Optional[str] = None):
        """Загрузка списка ОКПД кодов с учетом выбранного региона"""
        try:
            if not hasattr(self, 'okpd_results_list') or self.okpd_results_list is None:
                logger.warning("okpd_results_list отсутствует, пропускаем загрузку ОКПД")
                return

            logger.info("Загрузка стандартных ОКПД (search=%s)", search_text)
            region_combo = getattr(self, 'region_combo', None)
            self.okpd_manager.load_okpd_codes(self.okpd_results_list, region_combo, search_text)
        except (DatabaseConnectionError, DatabaseQueryError) as e:
            logger.error(f"Ошибка подключения к БД при загрузке ОКПД: {e}")
            if self.parent_widget and hasattr(self.parent_widget, '_handle_db_reconnection'):
                self.parent_widget._handle_db_reconnection()
        except Exception as e:
            logger.error(f"Ошибка при загрузке ОКПД кодов: {e}", exc_info=True)
    
    def on_okpd_search_changed(self, text: str):
        """Обработка изменения текста поиска ОКПД"""
        self.search_params_cache.save_okpd_search_text(text if text else None)
        
        if not hasattr(self, 'search_timer'):
            self.search_timer = QTimer()
            self.search_timer.setSingleShot(True)
            self.search_timer.timeout.connect(lambda: self.load_okpd_codes(self.okpd_search_input.text()))
        
        self.search_timer.stop()
        if text:
            self.search_timer.start(300)
        else:
            self.load_okpd_codes()
    
    def handle_add_okpd(self):
        """Обработка добавления выбранного ОКПД"""
        if hasattr(self, 'okpd_results_list') and self.okpd_results_list:
            self.okpd_manager.add_okpd(self.okpd_results_list, self.parent_widget)
            self.load_user_okpd_codes()
    
    def load_user_okpd_codes(self):
        """Загрузка и отображение добавленных ОКПД пользователя"""
        if not self.tender_repo:
            return
        
        try:
            # Очищаем контейнер
            while self.added_okpd_layout.count():
                item = self.added_okpd_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            logger.info(f"Загрузка пользовательских ОКПД для user_id={self.user_id}")
            user_okpd = self.tender_repo.get_user_okpd_codes(self.user_id)
        except (DatabaseConnectionError, DatabaseQueryError) as e:
            logger.error(f"Ошибка подключения к БД при загрузке пользовательских ОКПД: {e}")
            if self.parent_widget and hasattr(self.parent_widget, '_handle_db_reconnection'):
                self.parent_widget._handle_db_reconnection()
            return
        except Exception as e:
            logger.error(f"Ошибка при загрузке пользовательских ОКПД: {e}", exc_info=True)
            return
        
        if not user_okpd:
            no_data_label = QLabel("Нет добавленных кодов ОКПД")
            apply_label_style(no_data_label, 'normal')
            apply_text_style_light_italic(no_data_label)
            self.added_okpd_layout.addWidget(no_data_label)
            return
        
        # Создаем лейблы для каждого ОКПД
        for okpd in user_okpd:
            okpd_frame = QFrame()
            okpd_frame.setMinimumHeight(60)
            apply_frame_style(okpd_frame, 'chip')
            
            okpd_item_layout = QHBoxLayout(okpd_frame)
            okpd_item_layout.setContentsMargins(12, 10, 12, 10)
            
            code = okpd.get('okpd_code', '')
            name = okpd.get('okpd_name') or okpd.get('name', 'Без названия')
            
            label_text = f"{code} - {name[:60]}" if name else code
            okpd_label = QLabel(label_text)
            apply_label_style(okpd_label, 'chip')
            okpd_label.setWordWrap(True)
            okpd_item_layout.addWidget(okpd_label)
            
            okpd_item_layout.addStretch()
            
            # Кнопка удаления
            btn_remove = QPushButton("✕")
            btn_remove.setFixedSize(30, 30)
            apply_button_style(btn_remove, 'icon')
            btn_remove.clicked.connect(
                lambda checked, okpd_id=okpd['id']: self.handle_remove_okpd(okpd_id)
            )
            okpd_item_layout.addWidget(btn_remove)
            
            self.added_okpd_layout.addWidget(okpd_frame)
    
    def handle_remove_okpd(self, okpd_id: int):
        """Обработка удаления ОКПД"""
        self.okpd_manager.remove_okpd(okpd_id, self.parent_widget)
        self.load_user_okpd_codes()
    
    def load_regions(self):
        """Загрузка списка регионов в выпадающий список"""
        if not self.tender_repo:
            logger.warning("Репозиторий закупок не инициализирован, регионы не загружены")
            return
        
        try:
            if not hasattr(self, 'region_combo') or self.region_combo is None:
                logger.warning("region_combo не инициализирован")
                return
            
            self.region_combo.clear()
            self.region_combo.addItem("Все регионы", None)
            
            regions = self.tender_repo.get_all_regions()
            
            if not regions:
                logger.warning("Не удалось загрузить регионы из БД")
                return
            
            for region in regions:
                region_name = region.get('name', '')
                region_code = region.get('code', '')
                display_text = f"{region_name}"
                if region_code:
                    display_text = f"{region_code} - {region_name}"
                
                self.region_combo.addItem(display_text, region)
            
            logger.info(f"Загружено регионов: {len(regions)}")
            self._restore_region_from_cache()
            
        except (DatabaseConnectionError, DatabaseQueryError) as e:
            logger.error(f"Ошибка подключения к БД при загрузке регионов: {e}")
            if self.parent_widget and hasattr(self.parent_widget, '_handle_db_reconnection'):
                self.parent_widget._handle_db_reconnection()
            if hasattr(self, 'region_combo') and self.region_combo:
                self.region_combo.clear()
                self.region_combo.addItem("Все регионы", None)
        except Exception as e:
            logger.error(f"Ошибка при загрузке регионов: {e}")
            if hasattr(self, 'region_combo') and self.region_combo:
                self.region_combo.clear()
                self.region_combo.addItem("Все регионы", None)
    
    def on_region_changed(self, index: int):
        """Обработка изменения региона"""
        if getattr(self, '_is_initializing', False):
            logger.debug("Пропускаем очистку кэша (инициализация региона)")
            return

        if not hasattr(self, 'region_combo') or not self.region_combo:
            return
        
        # Получаем текущий регион из комбобокса
        current_region_data = self.region_combo.currentData()
        current_region_id = current_region_data.get('id') if current_region_data else None
        
        # Получаем закешированный регион
        cached_region_id = self.search_params_cache.get_region_id()
        
        # Очищаем кэш только если регион действительно изменился
        if current_region_id != cached_region_id:
            self.search_params_cache.clear_tenders_cache()
            logger.debug(f"Кэш закупок очищен из-за изменения региона: {cached_region_id} -> {current_region_id}")
        else:
            logger.debug(f"Регион не изменился ({current_region_id}), кэш не очищается")
        
        # Сохраняем текущий регион в кэш
        self.search_params_cache.save_region(current_region_id, current_region_data)
        logger.debug(f"Регион сохранен в кэш: {current_region_id}")
        
        if not hasattr(self, 'okpd_search_input') or self.okpd_search_input is None:
            return
        
        search_text = self.okpd_search_input.text() if self.okpd_search_input.text() else None
        self.search_params_cache.save_okpd_search_text(search_text)
        self.load_okpd_codes(search_text)
    
    def load_user_stop_words(self):
        """Загрузка и отображение стоп-слов пользователя"""
        if not self.tender_repo:
            return
        
        try:
            # Очищаем контейнер
            while self.stop_words_layout.count():
                item = self.stop_words_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            user_stop_words = self.tender_repo.get_user_stop_words(self.user_id)
        except (DatabaseConnectionError, DatabaseQueryError) as e:
            logger.error(f"Ошибка подключения к БД при загрузке стоп-слов: {e}")
            if self.parent_widget and hasattr(self.parent_widget, '_handle_db_reconnection'):
                self.parent_widget._handle_db_reconnection()
            return
        except Exception as e:
            logger.error(f"Ошибка при загрузке стоп-слов: {e}", exc_info=True)
            return
        
        if not user_stop_words:
            no_data_label = QLabel("Нет добавленных стоп-слов")
            apply_label_style(no_data_label, 'normal')
            apply_text_style_light_italic(no_data_label)
            self.stop_words_layout.addWidget(no_data_label)
            return
        
        # Формируем одну подпись с перечислением слов
        words_html_parts = []
        for stop_word_data in user_stop_words:
            stop_word_text = stop_word_data.get('stop_word', '')
            if not stop_word_text:
                continue
            word_id = stop_word_data.get('id')
            safe_text = html.escape(stop_word_text)
            words_html_parts.append(
                f"<span style='font-weight: 500;'>{safe_text}</span> "
                f"<a href='remove:{word_id}' style='color:#E53935;text-decoration:none;'>✕</a>"
            )
        
        words_label = QLabel()
        apply_label_style(words_label, 'normal')
        words_label.setWordWrap(True)
        words_label.setTextFormat(Qt.RichText)
        words_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        words_label.setOpenExternalLinks(False)
        words_label.setText(", ".join(words_html_parts))
        words_label.linkActivated.connect(self._handle_stop_word_link)
        self.stop_words_layout.addWidget(words_label)

    def load_document_stop_phrases(self):
        """Загрузка и отображение стоп-фраз анализа документации."""
        if not self.tender_repo:
            return

        try:
            while self.document_stop_phrases_layout.count():
                item = self.document_stop_phrases_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            phrases = self.tender_repo.get_document_stop_phrases(self.user_id)
        except (DatabaseConnectionError, DatabaseQueryError) as error:
            logger.error(f"Ошибка подключения к БД при загрузке стоп-фраз документации: {error}")
            if self.parent_widget and hasattr(self.parent_widget, '_handle_db_reconnection'):
                self.parent_widget._handle_db_reconnection()
            return
        except Exception as error:
            logger.error(f"Ошибка при загрузке стоп-фраз документации: {error}", exc_info=True)
            return

        if not phrases:
            no_data_label = QLabel("Нет добавленных стоп-фраз для анализа документации")
            apply_label_style(no_data_label, 'normal')
            apply_text_style_light_italic(no_data_label)
            self.document_stop_phrases_layout.addWidget(no_data_label)
            return

        parts = []
        for row in phrases:
            phrase_text = row.get("phrase", "")
            if not phrase_text:
                continue
            phrase_id = row.get("id")
            safe_text = html.escape(phrase_text)
            parts.append(
                f"<span style='font-weight: 500;'>{safe_text}</span> "
                f"<a href='remove-doc:{phrase_id}' style='color:#E53935;text-decoration:none;'>✕</a>"
            )

        label = QLabel()
        apply_label_style(label, 'normal')
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(False)
        label.setText(", ".join(parts))
        label.linkActivated.connect(self._handle_document_stop_phrase_link)
        self.document_stop_phrases_layout.addWidget(label)

    def handle_add_document_stop_phrases(self):
        """Обработка добавления стоп-фраз анализа документации."""
        if hasattr(self, 'document_stop_phrases_input'):
            input_text = self.document_stop_phrases_input.text()
            self.document_stop_phrases_manager.add_stop_phrases(input_text, self.parent_widget)
            self.document_stop_phrases_input.clear()
            self.load_document_stop_phrases()

    def handle_remove_document_stop_phrase(self, phrase_id: int):
        """Обработка удаления стоп-фразы анализа документации."""
        self.document_stop_phrases_manager.remove_stop_phrase(phrase_id, self.parent_widget)
        self.load_document_stop_phrases()

    def _handle_document_stop_phrase_link(self, link: str):
        """Обработка клика по ссылке удаления стоп-фразы анализа документации."""
        if link.startswith("remove-doc:"):
            try:
                phrase_id = int(link.split("remove-doc:")[1])
                self.handle_remove_document_stop_phrase(phrase_id)
            except ValueError:
                logger.error(f"Некорректный идентификатор стоп-фразы в ссылке: {link}")
    
    def handle_add_stop_words(self):
        """Обработка добавления стоп-слов"""
        if hasattr(self, 'stop_words_input'):
            input_text = self.stop_words_input.text()
            self.stop_words_manager.add_stop_words(input_text, self.parent_widget)
            self.stop_words_input.clear()
            self.load_user_stop_words()
    
    def handle_remove_stop_word(self, stop_word_id: int):
        """Обработка удаления стоп-слова"""
        self.stop_words_manager.remove_stop_word(stop_word_id, self.parent_widget)
        self.load_user_stop_words()
    
    def _handle_stop_word_link(self, link: str):
        """Обработка клика по ссылке удаления стоп-слова"""
        if link.startswith("remove:"):
            try:
                stop_word_id = int(link.split("remove:")[1])
                self.handle_remove_stop_word(stop_word_id)
            except ValueError:
                logger.error(f"Некорректный идентификатор стоп-слова в ссылке: {link}")
    
    def load_okpd_categories(self):
        """Загрузка и отображение категорий ОКПД пользователя"""
        try:
            categories_list = getattr(self, 'categories_list', None)
            category_filter_combo = getattr(self, 'category_filter_combo', None)
            self.categories_manager.load_categories(categories_list, category_filter_combo)
            self._restore_category_from_cache()
        except (DatabaseConnectionError, DatabaseQueryError) as e:
            logger.error(f"Ошибка подключения к БД при загрузке категорий: {e}")
            if self.parent_widget and hasattr(self.parent_widget, '_handle_db_reconnection'):
                self.parent_widget._handle_db_reconnection()
        except Exception as e:
            logger.error(f"Ошибка при загрузке категорий: {e}", exc_info=True)
    
    def on_category_filter_changed(self, index: int):
        """Обработка изменения выбранной категории для фильтрации"""
        if getattr(self, '_is_initializing', False):
            logger.debug("Пропускаем очистку кэша (инициализация категории)")
            return

        # Пропускаем очистку кэша, если категория восстанавливается из кэша
        if getattr(self, '_restoring_from_cache', False):
            logger.debug("Пропускаем очистку кэша (восстановление категории из кэша)")
            return

        if not hasattr(self, 'category_filter_combo') or not self.category_filter_combo:
            return
        
        # Получаем текущую категорию из комбобокса
        current_category_id = self.category_filter_combo.currentData()
        
        # Получаем закешированную категорию
        cached_category_id = self.search_params_cache.get_category_id()
        
        # Очищаем кэш только если категория действительно изменилась
        # Если cached_category_id == None, это первый запуск, не очищаем кэш
        if cached_category_id is not None and current_category_id != cached_category_id:
            self.search_params_cache.clear_tenders_cache()
            logger.debug(f"Кэш закупок очищен из-за изменения категории: {cached_category_id} -> {current_category_id}")
        else:
            if cached_category_id is None:
                logger.debug(f"Первая установка категории ({current_category_id}), кэш не очищается")
            else:
                logger.debug(f"Категория не изменилась ({current_category_id}), кэш не очищается")
        
        # Сохраняем текущую категорию в кэш
        self.search_params_cache.save_category(current_category_id)
        logger.debug(f"Категория сохранена в кэш: {current_category_id}")
        
        # Уведомляем родительский виджет об изменении категории
        if self.parent_widget and hasattr(self.parent_widget, 'on_category_filter_changed'):
            self.parent_widget.on_category_filter_changed(index)
    
    def handle_create_category(self):
        """Обработка создания новой категории ОКПД"""
        if hasattr(self, 'category_name_input'):
            category_name = self.category_name_input.text()
            category_id = self.categories_manager.create_category(category_name, self.parent_widget)
            if category_id:
                self.category_name_input.clear()
                self.load_okpd_categories()
    
    def handle_delete_category(self):
        """Обработка удаления категории ОКПД"""
        if hasattr(self, 'categories_list'):
            success = self.categories_manager.delete_category(self.categories_list, self.parent_widget)
            if success:
                self.load_okpd_categories()
                self.load_user_okpd_codes()
    
    def handle_show_tenders(self):
        """Обработка нажатия кнопки 'Показать тендеры'"""
        if self.parent_widget and hasattr(self.parent_widget, 'handle_show_tenders'):
            self.parent_widget.handle_show_tenders()
    
    def _restore_region_from_cache(self) -> None:
        """Восстановление выбранного региона из кэша"""
        if not hasattr(self, 'region_combo') or self.region_combo is None:
            return
        
        cached_region_id = self.search_params_cache.get_region_id()
        if cached_region_id is None:
            return
        
        for i in range(self.region_combo.count()):
            region_data = self.region_combo.itemData(i)
            if region_data and region_data.get('id') == cached_region_id:
                self.region_combo.blockSignals(True)
                self.region_combo.setCurrentIndex(i)
                self.region_combo.blockSignals(False)
                logger.info(f"Восстановлен регион из кэша: {cached_region_id}")
                return
    
    def _restore_category_from_cache(self) -> None:
        """Восстановление выбранной категории из кэша"""
        if not hasattr(self, 'category_filter_combo') or self.category_filter_combo is None:
            return
        
        cached_category_id = self.search_params_cache.get_category_id()
        if cached_category_id is None:
            return
        
        for i in range(self.category_filter_combo.count()):
            category_id = self.category_filter_combo.itemData(i)
            if category_id == cached_category_id:
                # Устанавливаем флаг, что мы восстанавливаем из кэша
                self._restoring_from_cache = True
                self.category_filter_combo.blockSignals(True)
                self.category_filter_combo.setCurrentIndex(i)
                self.category_filter_combo.blockSignals(False)
                self._restoring_from_cache = False
                logger.info(f"Восстановлена категория из кэша: {cached_category_id}")
                return
    
    def get_category_filter_combo(self):
        """Получение комбобокса фильтра категорий (для использования в родительском виджете)"""
        return getattr(self, 'category_filter_combo', None)

