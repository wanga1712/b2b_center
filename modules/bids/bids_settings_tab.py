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
    apply_scroll_area_style, apply_list_widget_style, apply_text_style_light_italic,
    COLORS, SIZES, FONT_SIZES
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
        self._settings_loaded_from_db = False
        self._init_settings_data()
        self._is_initializing = False
    
    def init_ui(self):
        """Инициализация пользовательского интерфейса в стиле Salesforce"""
        from modules.bids.salesforce_settings_ui import create_salesforce_section_card
        
        # Создаем контейнер с прокруткой для всей вкладки
        scroll_widget = QWidget()
        settings_layout = QVBoxLayout(scroll_widget)
        settings_layout.setContentsMargins(30, 30, 30, 30)
        settings_layout.setSpacing(20)
        
        # Создаем ScrollArea для прокрутки всего контента
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setStyleSheet(
            f"QScrollArea {{ border: none; background: {COLORS.get('background', COLORS['secondary'])}; }}"
        )
        
        tab_layout = QVBoxLayout(self)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)
        tab_layout.addWidget(scroll_area)
        
        # Заголовок в стиле Salesforce
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        settings_label = QLabel("⚙️ Настройки поиска закупок")
        settings_label.setStyleSheet(
            f"font-size: {FONT_SIZES['h1']}; font-weight: bold; color: {COLORS['text_dark']};"
        )
        header_layout.addWidget(settings_label)
        
        subtitle_label = QLabel("Настройте параметры поиска и фильтрации закупок")
        subtitle_label.setStyleSheet(
            f"font-size: {FONT_SIZES['normal']}; color: {COLORS['text_light']};"
        )
        header_layout.addWidget(subtitle_label)
        
        settings_layout.addLayout(header_layout)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background: {COLORS['border']}; max-height: 2px; margin: 10px 0;")
        settings_layout.addWidget(separator)
        
        # Создаем все секции используя билдер
        from modules.bids.settings_ui_builders.sections_builder import SettingsSectionsBuilder
        
        # Фильтрация по категории
        widgets1 = SettingsSectionsBuilder.build_category_filter_section(settings_layout)
        self.category_filter_combo = widgets1['category_filter_combo']
        self.category_filter_combo.currentIndexChanged.connect(self.on_category_filter_changed)
        
        # Выбор ОКПД
        widgets2 = SettingsSectionsBuilder.build_okpd_section(settings_layout)
        self.region_combo = widgets2['region_combo']
        self.okpd_search_input = widgets2['okpd_search_input']
        self.okpd_results_list = widgets2['okpd_results_list']
        widgets2['btn_add_okpd'].clicked.connect(self.handle_add_okpd)
        self.okpd_search_input.textChanged.connect(self.on_okpd_search_changed)
        
        # Управление категориями
        widgets3 = SettingsSectionsBuilder.build_categories_section(settings_layout)
        self.categories_list = widgets3['categories_list']
        widgets3['btn_create_category'].clicked.connect(self.handle_create_category)
        widgets3['btn_rename_category'].clicked.connect(self.handle_rename_category)
        widgets3['btn_delete_category'].clicked.connect(self.handle_delete_category)
        widgets3['btn_assign_category'].clicked.connect(self.handle_assign_category)
        
        # Добавленные ОКПД
        widgets4 = SettingsSectionsBuilder.build_added_okpd_section(settings_layout)
        self.added_okpd_container = widgets4['added_okpd_container']
        self.added_okpd_layout = widgets4['added_okpd_layout']
        
        # Стоп-слова
        widgets5 = SettingsSectionsBuilder.build_stop_words_section(settings_layout)
        self.stop_word_input = widgets5['stop_word_input']
        self.stop_words_container = widgets5['stop_words_container']
        self.stop_words_layout = widgets5['stop_words_layout']
        widgets5['btn_add_stop_word'].clicked.connect(self.handle_add_stop_words)
        
        # Стоп-фразы для документов
        widgets6 = SettingsSectionsBuilder.build_document_stop_phrases_section(settings_layout)
        self.document_stop_phrase_input = widgets6['document_stop_phrase_input']
        self.document_stop_phrases_container = widgets6['document_stop_phrases_container']
        self.document_stop_phrases_layout = widgets6['document_stop_phrases_layout']
        widgets6['btn_add_phrase'].clicked.connect(self.handle_add_document_stop_phrases)
        
        # Кнопки применения настроек
        widgets7 = SettingsSectionsBuilder.build_show_tenders_section(settings_layout)
        widgets7['btn_update_data'].clicked.connect(self.handle_update_data)
        widgets7['btn_save_settings'].clicked.connect(self.handle_save_settings)
        widgets7['btn_back'].clicked.connect(self.handle_back_to_dashboard)
        
        # Загружаем регионы после создания всех элементов
        self._init_regions()
    
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
            
            # Загружаем сохраненные настройки пользователя из БД
            self._load_user_settings_from_db()
            
            # Загружаем регионы (внутри вызывается _restore_region_from_cache)
            self.load_regions()
            
            self.load_okpd_codes()
            # Загружаем категории (внутри вызывается _restore_category_from_cache)
            self.load_okpd_categories()
            self.load_user_okpd_codes()
            self.load_user_stop_words()
            self.load_document_stop_phrases()
        except Exception as e:
            logger.error(f"Ошибка при инициализации данных настроек: {e}")
    
    def _load_user_settings_from_db(self) -> None:
        """Загрузка сохраненных настроек пользователя из БД"""
        try:
            if not self.tender_repo or not hasattr(self.tender_repo, 'get_user_search_settings'):
                logger.debug("Репозиторий не поддерживает загрузку настроек поиска")
                return
            
            settings = self.tender_repo.get_user_search_settings(self.user_id)
            if settings:
                region_id = settings.get('region_id')
                category_id = settings.get('category_id')
                
                # Сохраняем в кэш
                if self.search_params_cache:
                    if region_id is not None:
                        # Загружаем данные региона для кэша
                        regions = self.tender_repo.get_all_regions()
                        region_data = next((r for r in regions if r.get('id') == region_id), None)
                        self.search_params_cache.save_region(region_id, region_data)
                    
                    if category_id is not None:
                        self.search_params_cache.save_category(category_id)
                    
                    # Устанавливаем флаг, что настройки были сохранены
                    self.search_params_cache.set_settings_saved(True)
                    
                    logger.info(f"Настройки поиска загружены из БД для пользователя {self.user_id}: region_id={region_id}, category_id={category_id}")
                    
                    # Устанавливаем флаг для восстановления в UI после загрузки регионов и категорий
                    self._settings_loaded_from_db = True
                else:
                    logger.warning("search_params_cache не инициализирован")
            else:
                logger.debug(f"Настройки поиска не найдены в БД для пользователя {self.user_id}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке настроек поиска из БД: {e}", exc_info=True)
    
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
        if hasattr(self, 'document_stop_phrase_input'):
            input_text = self.document_stop_phrase_input.text()
            self.document_stop_phrases_manager.add_stop_phrases(input_text, self.parent_widget)
            self.document_stop_phrase_input.clear()
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
        from PyQt5.QtWidgets import QInputDialog
        
        category_name, ok = QInputDialog.getText(
            self.parent_widget,
            "Создание категории",
            "Введите название категории:"
        )
        
        if ok and category_name.strip():
            category_id = self.categories_manager.create_category(category_name.strip(), self.parent_widget)
            if category_id:
                self.load_okpd_categories()
    
    def handle_rename_category(self):
        """Обработка переименования категории ОКПД"""
        from PyQt5.QtWidgets import QInputDialog, QMessageBox
        
        if not hasattr(self, 'categories_list'):
            return
        
        current_item = self.categories_list.currentItem()
        if not current_item:
            QMessageBox.warning(self.parent_widget, "Предупреждение", "Выберите категорию для переименования")
            return
        
        category_data = current_item.data(Qt.UserRole)
        if not category_data:
            return
        
        old_name = category_data.get('name', '')
        new_name, ok = QInputDialog.getText(
            self.parent_widget,
            "Переименование категории",
            "Новое название:",
            text=old_name
        )
        
        if ok and new_name.strip():
            # Используем репозиторий для обновления категории
            success = self.tender_repo.update_okpd_category(
                category_id=category_data.get('id'),
                user_id=self.user_id,
                name=new_name.strip()
            )
            if success:
                self.load_okpd_categories()
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self.parent_widget, "Ошибка", "Не удалось переименовать категорию")
    
    def handle_assign_category(self):
        """Обработка назначения категории выбранному ОКПД"""
        # Получаем выбранный ОКПД из контейнера
        # Нужно найти выбранный элемент (через фокус или через клик)
        # Для простоты используем диалог выбора из списка добавленных ОКПД
        from PyQt5.QtWidgets import QInputDialog, QMessageBox
        
        if not hasattr(self, 'added_okpd_layout'):
            return
        
        # Получаем список добавленных ОКПД
        try:
            user_okpd = self.tender_repo.get_user_okpd_codes(self.user_id)
            if not user_okpd:
                QMessageBox.information(self.parent_widget, "Информация", "Нет добавленных ОКПД кодов")
                return
            
            # Создаем список для выбора
            okpd_list = [f"{okpd.get('okpd_code', '')} - {okpd.get('okpd_name', 'Без названия')[:50]}" for okpd in user_okpd]
            selected, ok = QInputDialog.getItem(
                self.parent_widget,
                "Выбор ОКПД",
                "Выберите ОКПД для назначения категории:",
                okpd_list,
                0,
                False
            )
            
            if not ok:
                return
            
            # Находим выбранный ОКПД
            selected_index = okpd_list.index(selected)
            selected_okpd = user_okpd[selected_index]
            okpd_id = selected_okpd['id']
            okpd_code = selected_okpd.get('okpd_code', '')
            
            # Получаем категории
            categories = self.tender_repo.get_okpd_categories(self.user_id)
            if not categories:
                QMessageBox.information(self.parent_widget, "Информация", "Нет созданных категорий")
                return
            
            category_names = [cat.get('name', 'Без названия') for cat in categories]
            category_names.insert(0, "Без категории")
            
            selected_category, ok = QInputDialog.getItem(
                self.parent_widget,
                "Выбор категории",
                f"Выберите категорию для ОКПД {okpd_code}:",
                category_names,
                0,
                False
            )
            
            if ok and selected_category != "Без категории":
                category_id = None
                for cat in categories:
                    if cat.get('name') == selected_category:
                        category_id = cat.get('id')
                        break
                
                if category_id:
                    success = self.tender_repo.assign_okpd_to_category(
                        user_id=self.user_id,
                        okpd_id=okpd_id,
                        category_id=category_id
                    )
                    if success:
                        QMessageBox.information(self.parent_widget, "Успех", f"Категория назначена ОКПД {okpd_code}")
                        self.load_user_okpd_codes()
                    else:
                        QMessageBox.warning(self.parent_widget, "Ошибка", "Не удалось назначить категорию")
        except Exception as e:
            logger.error(f"Ошибка при назначении категории: {e}", exc_info=True)
            QMessageBox.warning(self.parent_widget, "Ошибка", f"Ошибка при назначении категории: {str(e)}")
    
    def handle_delete_category(self):
        """Обработка удаления категории ОКПД"""
        if hasattr(self, 'categories_list'):
            success = self.categories_manager.delete_category(self.categories_list, self.parent_widget)
            if success:
                self.load_okpd_categories()
                self.load_user_okpd_codes()
    
    def handle_save_settings(self):
        """Обработка нажатия кнопки 'Сохранить настройки'"""
        try:
            # Получаем текущие значения региона и категории из кэша
            region_id = self.search_params_cache.get_region_id() if hasattr(self, 'search_params_cache') and self.search_params_cache else None
            category_id = self.search_params_cache.get_category_id() if hasattr(self, 'search_params_cache') and self.search_params_cache else None
            
            # Сохраняем настройки в БД
            if self.tender_repo and hasattr(self.tender_repo, 'save_user_search_settings'):
                success = self.tender_repo.save_user_search_settings(self.user_id, region_id, category_id)
                if success:
                    logger.info(f"Настройки поиска сохранены в БД для пользователя {self.user_id}: region_id={region_id}, category_id={category_id}")
                else:
                    logger.warning(f"Не удалось сохранить настройки поиска в БД для пользователя {self.user_id}")
            
            # Сохраняем флаг, что настройки были сохранены пользователем
            if hasattr(self, 'search_params_cache') and self.search_params_cache:
                self.search_params_cache.set_settings_saved(True)
            
            # Показываем уведомление
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Настройки сохранены",
                "Настройки поиска сохранены.\n\n"
                "Теперь вы можете перейти в разделы закупок,\n"
                "и данные будут загружены по вашим настройкам."
            )
            
            # Возвращаемся на Dashboard (НЕ загружаем закупки)
            if self.parent_widget and hasattr(self.parent_widget, 'stack_widget'):
                self.parent_widget.stack_widget.setCurrentIndex(0)  # 0 = Dashboard
            
            logger.info("Настройки поиска сохранены пользователем, возврат на Dashboard")
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроек: {e}", exc_info=True)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось сохранить настройки:\n{e}"
            )
    
    def handle_update_data(self):
        """Обработка нажатия кнопки 'Обновить данные' - применяет настройки без сохранения"""
        try:
            logger.info("Обновление данных с текущими настройками (без сохранения в БД)")
            
            # Обновляем счетчики через родительский виджет
            if self.parent_widget and hasattr(self.parent_widget, 'handle_show_tenders'):
                self.parent_widget.handle_show_tenders()
                logger.info("Данные обновлены успешно")
                
                # Показываем уведомление об успешном обновлении
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "Данные обновлены",
                    "Счетчики закупок обновлены с текущими настройками.\n\n"
                    "Настройки не сохранены в БД и будут сброшены после перезапуска."
                )
            else:
                logger.warning("Родительский виджет не поддерживает обновление данных")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "Информация",
                    "Родительский виджет не поддерживает обновление данных.\n\n"
                    "Настройки не сохранены в БД и будут сброшены после перезапуска."
                )
        except Exception as e:
            logger.error(f"Ошибка при обновлении данных: {e}", exc_info=True)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось обновить данные:\n{e}"
            )
    
    def handle_back_to_dashboard(self):
        """Обработка нажатия кнопки 'Назад к дашборду' - возврат без сохранения"""
        try:
            logger.info("Возврат на дашборд без сохранения настроек")
            
            # Возвращаемся на Dashboard
            if self.parent_widget and hasattr(self.parent_widget, 'stack_widget'):
                # Если есть stack_widget (BidsWidget), переключаемся на Dashboard
                self.parent_widget.stack_widget.setCurrentIndex(0)  # 0 = Dashboard
                logger.info("Возврат на Dashboard выполнен через stack_widget")
            elif self.parent_widget and hasattr(self.parent_widget, 'on_back_clicked'):
                # Если это PurchasesSubmenuWidget, используем его метод для возврата в CRM
                self.parent_widget.on_back_clicked()
                logger.info("Возврат через on_back_clicked выполнен")
            else:
                # Если настройки встроены в виджет (PurchasesSubmenuWidget), 
                # просто прокручиваем вверх - настройки уже на дашборде
                logger.info("Настройки встроены в дашборд, возврат не требуется")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "Информация",
                    "Вы уже находитесь на дашборде закупок.\n\n"
                    "Настройки не сохранены и будут сброшены после перезапуска."
                )
        except Exception as e:
            logger.error(f"Ошибка при возврате на дашборд: {e}", exc_info=True)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось вернуться на дашборд:\n{e}"
            )
    
    def handle_show_tenders(self):
        """Обработка нажатия кнопки 'Показать тендеры' (для обратной совместимости)"""
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

