"""
Виджет для управления торгами (44ФЗ и 223ФЗ)

Виджет предоставляет интерфейс для:
- Управления новыми торгами 44ФЗ и 223ФЗ через канбан-доски
- Просмотра разыгранных торгов
- Настройки параметров торгов
- Отслеживания торгов в работе
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QFrame,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QScrollArea,
    QMessageBox, QComboBox
)
from PyQt5.QtCore import Qt, QTimer
from typing import Optional, Dict, Any, List
from pathlib import Path
from loguru import logger
import re

# Импортируем единые стили
from modules.styles.general_styles import (
    apply_label_style, apply_frame_style, apply_input_style, apply_button_style,
    COLORS, FONT_SIZES, SIZES, apply_text_style_light_italic
)

# Импортируем виджеты для торгов
from modules.bids.tender_list_widget import TenderListWidget

# Импортируем репозиторий для работы с торгами
from services.tender_repository import TenderRepository
from services.document_search_service import DocumentSearchService
from core.tender_database import TenderDatabaseManager
from config.settings import config
from core.database import DatabaseManager

# DOCUMENT_DOWNLOAD_DIR - путь к директории для скачивания документов из ЕИС
# Настраивается через переменную окружения DOCUMENT_DOWNLOAD_DIR в .env файле
# Пример: DOCUMENT_DOWNLOAD_DIR=C:\Projects\Documents\Tenders


class BidsWidget(QWidget):
    """
    Виджет для управления торгами
    
    Содержит вкладки для различных типов торгов и их статусов.
    """
    
    def __init__(self, product_db_manager: Optional[DatabaseManager] = None):
        super().__init__()
        
        # Инициализация подключения к БД tender_monitor (обязательно)
        if not config.tender_database:
            error_msg = "Конфигурация БД tender_monitor не задана. Проверьте переменные окружения в .env файле."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            self.tender_db_manager = TenderDatabaseManager(config.tender_database)
            self.tender_db_manager.connect()
            self.tender_repo = TenderRepository(self.tender_db_manager)
            logger.info("Подключение к БД tender_monitor установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к БД tender_monitor: {e}")
            raise  # Пробрасываем ошибку, так как подключение обязательно
        
        # Временный ID пользователя (позже будет из системы авторизации)
        self.current_user_id = 1
        self.product_db_manager = product_db_manager
        self.document_search_service: Optional[DocumentSearchService] = None
        if self.product_db_manager:
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
            logger.warning("Сервис поиска документации недоступен: не передан менеджер БД продуктов")
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок раздела
        header_frame = QFrame()
        apply_frame_style(header_frame, 'content')
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        title = QLabel("📈 Торги")
        apply_label_style(title, 'h1')
        header_layout.addWidget(title)
        
        main_layout.addWidget(header_frame)
        
        # Вкладки для различных разделов торгов
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                background: {COLORS['secondary']};
                border-radius: {SIZES['border_radius_normal']}px;
            }}
            QTabBar::tab {{
                background: {COLORS['white']};
                color: {COLORS['text_dark']};
                padding: {SIZES['padding_normal']}px {SIZES['padding_large']}px;
                margin-right: 2px;
                border-top-left-radius: {SIZES['border_radius_small']}px;
                border-top-right-radius: {SIZES['border_radius_small']}px;
                font-size: {FONT_SIZES['normal']};
            }}
            QTabBar::tab:selected {{
                background: {COLORS['primary']};
                color: {COLORS['white']};
            }}
            QTabBar::tab:hover {{
                background: {COLORS['secondary']};
            }}
        """)
        
        # === ВКЛАДКА "НАСТРОЙКИ" ===
        settings_tab = self.create_settings_tab()
        self.tabs.addTab(settings_tab, "Настройки")
        
        # === ВКЛАДКА "НОВЫЕ ТОРГИ 44ФЗ" ===
        self.tenders_44fz_widget = TenderListWidget(
            document_search_service=self.document_search_service,
        )
        self.tabs.addTab(self.tenders_44fz_widget, "Новые торги 44ФЗ")
        # Загружаем торги при первом показе вкладки
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # === ВКЛАДКА "НОВЫЕ ТОРГИ 223ФЗ" ===
        self.tenders_223fz_widget = TenderListWidget(
            document_search_service=self.document_search_service,
        )
        self.tabs.addTab(self.tenders_223fz_widget, "Новые торги 223ФЗ")
        
        # === ВКЛАДКА "РАЗЫГРАННЫЕ ТОРГИ 44ФЗ" ===
        # TODO: Реализовать позже
        won_44fz_tab = QWidget()
        won_44fz_layout = QVBoxLayout(won_44fz_tab)
        won_44fz_label = QLabel("Разыгранные торги 44ФЗ")
        apply_label_style(won_44fz_label, 'h2')
        won_44fz_layout.addWidget(won_44fz_label)
        self.tabs.addTab(won_44fz_tab, "Разыгранные торги 44ФЗ")
        
        # === ВКЛАДКА "РАЗЫГРАННЫЕ ТОРГИ 223ФЗ" ===
        # TODO: Реализовать позже
        won_223fz_tab = QWidget()
        won_223fz_layout = QVBoxLayout(won_223fz_tab)
        won_223fz_label = QLabel("Разыгранные торги 223ФЗ")
        apply_label_style(won_223fz_label, 'h2')
        won_223fz_layout.addWidget(won_223fz_label)
        self.tabs.addTab(won_223fz_tab, "Разыгранные торги 223ФЗ")
        
        # === ВКЛАДКА "В РАБОТЕ" ===
        in_work_tab = QWidget()
        in_work_layout = QVBoxLayout(in_work_tab)
        in_work_layout.setContentsMargins(20, 20, 20, 20)
        
        in_work_label = QLabel("Торги в работе")
        apply_label_style(in_work_label, 'h2')
        in_work_layout.addWidget(in_work_label)
        
        in_work_info = QLabel("Раздел торгов в работе будет реализован позже")
        apply_label_style(in_work_info, 'normal')
        apply_text_style_light_italic(in_work_info)
        in_work_layout.addWidget(in_work_info)
        in_work_layout.addStretch()
        
        self.tabs.addTab(in_work_tab, "В работе")
        
        # Добавляем вкладки в основной layout
        main_layout.addWidget(self.tabs)
    
    def on_tab_changed(self, index: int):
        """Обработка смены вкладки - загрузка данных при первом открытии"""
        tab_text = self.tabs.tabText(index)
        
        if tab_text == "Новые торги 44ФЗ":
            if not hasattr(self.tenders_44fz_widget, '_loaded'):
                self.load_tenders_44fz()
                self.tenders_44fz_widget._loaded = True
        elif tab_text == "Новые торги 223ФЗ":
            if not hasattr(self.tenders_223fz_widget, '_loaded'):
                self.load_tenders_223fz()
                self.tenders_223fz_widget._loaded = True
    
    def load_tenders_44fz(self):
        """Загрузка новых торгов 44ФЗ"""
        if not self.tender_repo:
            logger.warning("Репозиторий торгов не инициализирован")
            return
        
        # Показываем индикатор загрузки
        self.tenders_44fz_widget.show_loading()
        
        # Получаем настройки пользователя
        user_okpd = self.tender_repo.get_user_okpd_codes(self.current_user_id)
        user_okpd_codes = [okpd.get('okpd_code', '') for okpd in user_okpd if okpd.get('okpd_code')]
        
        user_stop_words_data = self.tender_repo.get_user_stop_words(self.current_user_id)
        user_stop_words = [sw.get('stop_word', '') for sw in user_stop_words_data if sw.get('stop_word')]
        
        # TODO: Получить region_id из настроек пользователя (пока None = все регионы)
        region_id = None
        
        # Загружаем торги в отдельном потоке (упрощенная версия - можно улучшить)
        try:
            tenders = self.tender_repo.get_new_tenders_44fz(
                user_id=self.current_user_id,
                user_okpd_codes=user_okpd_codes,
                user_stop_words=user_stop_words,
                region_id=region_id,
                limit=1000  # Увеличено до 1000 торгов для отображения
            )
            # Извлекаем информацию о количестве из первого элемента
            total_count = None
            if tenders and '_total_count' in tenders[0]:
                total_count = tenders[0].pop('_total_count', len(tenders))
                tenders[0].pop('_loaded_count', None)  # Удаляем служебное поле
            
            logger.info(f"Отображаем торгов 44ФЗ: {len(tenders)} (всего в БД: {total_count})")
            self.tenders_44fz_widget.set_tenders(tenders, total_count)
            if self.document_search_service:
                self.document_search_service.ensure_products_loaded()
        except Exception as e:
            logger.error(f"Ошибка при загрузке торгов 44ФЗ: {e}")
            self.tenders_44fz_widget.hide_loading()
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить торги:\n{e}")
    
    def load_tenders_223fz(self):
        """Загрузка новых торгов 223ФЗ"""
        if not self.tender_repo:
            logger.warning("Репозиторий торгов не инициализирован")
            return
        
        # Показываем индикатор загрузки
        self.tenders_223fz_widget.show_loading()
        
        # Получаем настройки пользователя
        user_okpd = self.tender_repo.get_user_okpd_codes(self.current_user_id)
        user_okpd_codes = [okpd.get('okpd_code', '') for okpd in user_okpd if okpd.get('okpd_code')]
        
        user_stop_words_data = self.tender_repo.get_user_stop_words(self.current_user_id)
        user_stop_words = [sw.get('stop_word', '') for sw in user_stop_words_data if sw.get('stop_word')]
        
        # TODO: Получить region_id из настроек пользователя (пока None = все регионы)
        region_id = None
        
        # Загружаем торги
        try:
            tenders = self.tender_repo.get_new_tenders_223fz(
                user_id=self.current_user_id,
                user_okpd_codes=user_okpd_codes,
                user_stop_words=user_stop_words,
                region_id=region_id,
                limit=1000  # Увеличено до 1000 торгов для отображения
            )
            # Извлекаем информацию о количестве из первого элемента
            total_count = None
            if tenders and '_total_count' in tenders[0]:
                total_count = tenders[0].pop('_total_count', len(tenders))
                tenders[0].pop('_loaded_count', None)  # Удаляем служебное поле
            
            logger.info(f"Отображаем торгов 223ФЗ: {len(tenders)} (всего в БД: {total_count})")
            self.tenders_223fz_widget.set_tenders(tenders, total_count)
            if self.document_search_service:
                self.document_search_service.ensure_products_loaded()
        except Exception as e:
            logger.error(f"Ошибка при загрузке торгов 223ФЗ: {e}")
            self.tenders_223fz_widget.hide_loading()
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить торги:\n{e}")
    
    def create_settings_tab(self) -> QWidget:
        """
        Создание вкладки настроек с выбором кодов ОКПД
        
        Returns:
            Виджет с настройками
        """
        # Создаем контейнер с прокруткой для всей вкладки
        scroll_widget = QWidget()
        settings_layout = QVBoxLayout(scroll_widget)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(15)
        
        # Создаем ScrollArea для прокрутки всего контента
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: {COLORS['secondary']};
            }}
        """)
        
        settings_tab = QWidget()
        tab_layout = QVBoxLayout(settings_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)
        tab_layout.addWidget(scroll_area)
        
        # Заголовок
        settings_label = QLabel("Настройки торгов")
        apply_label_style(settings_label, 'h2')
        settings_layout.addWidget(settings_label)
        
        # Раздел выбора ОКПД
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
        
        # Контейнер для списка ОКПД с прокруткой
        self.okpd_results_list = QListWidget()
        self.okpd_results_list.setMinimumHeight(300)
        self.okpd_results_list.setMaximumHeight(400)
        self.okpd_results_list.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
                background: {COLORS['white']};
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QListWidget::item:hover {{
                background: {COLORS['secondary']};
            }}
            QListWidget::item:selected {{
                background: {COLORS['primary']};
                color: {COLORS['white']};
            }}
        """)
        okpd_layout.addWidget(self.okpd_results_list)
        
        settings_layout.addWidget(okpd_frame)
        
        # Раздел добавленных ОКПД
        added_frame = QFrame()
        apply_frame_style(added_frame, 'content')
        added_layout = QVBoxLayout(added_frame)
        added_layout.setContentsMargins(15, 15, 15, 15)
        added_layout.setSpacing(10)
        
        added_title = QLabel("Добавленные коды ОКПД")
        apply_label_style(added_title, 'h3')
        added_layout.addWidget(added_title)
        
        # Контейнер для лейблов с добавленными ОКПД
        self.added_okpd_container = QWidget()
        self.added_okpd_layout = QVBoxLayout(self.added_okpd_container)
        self.added_okpd_layout.setSpacing(8)
        self.added_okpd_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.added_okpd_container)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMaximumHeight(500)  # Увеличена максимальная высота
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
                background: {COLORS['white']};
            }}
        """)
        added_layout.addWidget(scroll_area)
        
        settings_layout.addWidget(added_frame)
        
        # === РАЗДЕЛ СТОП-СЛОВ ===
        stop_words_frame = QFrame()
        apply_frame_style(stop_words_frame, 'content')
        stop_words_layout = QVBoxLayout(stop_words_frame)
        stop_words_layout.setContentsMargins(15, 15, 15, 15)
        stop_words_layout.setSpacing(10)
        
        stop_words_title = QLabel("Стоп-слова")
        apply_label_style(stop_words_title, 'h3')
        stop_words_layout.addWidget(stop_words_title)
        
        stop_words_info = QLabel("Стоп-слова используются для фильтрации торгов. Торги, содержащие стоп-слова, будут исключены из результатов.")
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
        stop_words_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
                background: {COLORS['white']};
            }}
        """)
        stop_words_layout.addWidget(stop_words_scroll)
        
        settings_layout.addWidget(stop_words_frame)
        
        # Загружаем регионы после создания всех элементов
        # Отключаем сигнал при загрузке, чтобы избежать вызова on_region_changed
        try:
            self.region_combo.blockSignals(True)
            self.load_regions()
            self.region_combo.blockSignals(False)
            # Подключаем сигнал после загрузки
            self.region_combo.currentIndexChanged.connect(self.on_region_changed)
        except Exception as e:
            logger.error(f"Ошибка при инициализации регионов: {e}")
            if hasattr(self, 'region_combo') and self.region_combo:
                self.region_combo.blockSignals(False)
        
        # Загружаем все ОКПД при инициализации
        self.load_okpd_codes()
        
        # Загружаем добавленные ОКПД пользователя
        self.load_user_okpd_codes()
        
        # Загружаем стоп-слова пользователя
        self.load_user_stop_words()
        
        return settings_tab
    
    def load_okpd_codes(self, search_text: Optional[str] = None):
        """Загрузка списка ОКПД кодов с учетом выбранного региона"""
        if not self.tender_repo:
            logger.warning("Репозиторий торгов не инициализирован, ОКПД не загружены")
            return
        
        if not hasattr(self, 'okpd_results_list') or self.okpd_results_list is None:
            logger.warning("okpd_results_list не инициализирован")
            return
        
        try:
            self.okpd_results_list.clear()
            
            # Получаем выбранный регион
            region_id = None
            if hasattr(self, 'region_combo') and self.region_combo and self.region_combo.currentIndex() > 0:
                region_data = self.region_combo.currentData()
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
                item.setData(Qt.UserRole, okpd)  # Сохраняем полные данные
                self.okpd_results_list.addItem(item)
            
            if len(okpd_codes) == 0:
                # Добавляем сообщение, если ничего не найдено
                no_results_item = QListWidgetItem("ОКПД коды не найдены")
                no_results_item.setFlags(no_results_item.flags() & ~Qt.ItemIsSelectable)
                self.okpd_results_list.addItem(no_results_item)
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке ОКПД кодов: {e}")
            error_item = QListWidgetItem(f"Ошибка загрузки: {str(e)}")
            error_item.setFlags(error_item.flags() & ~Qt.ItemIsSelectable)
            self.okpd_results_list.addItem(error_item)
    
    def on_okpd_search_changed(self, text: str):
        """Обработка изменения текста поиска ОКПД"""
        # Используем таймер для задержки поиска
        if not hasattr(self, 'search_timer'):
            self.search_timer = QTimer()
            self.search_timer.setSingleShot(True)
            self.search_timer.timeout.connect(lambda: self.load_okpd_codes(self.okpd_search_input.text()))
        
        self.search_timer.stop()
        if text:
            self.search_timer.start(300)  # Задержка 300мс
        else:
            self.load_okpd_codes()
    
    def handle_add_okpd(self):
        """Обработка добавления выбранного ОКПД"""
        if not self.tender_repo:
            QMessageBox.warning(self, "Ошибка", "Нет подключения к базе данных")
            return
        
        current_item = self.okpd_results_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Предупреждение", "Выберите код ОКПД из списка")
            return
        
        okpd_data = current_item.data(Qt.UserRole)
        if not okpd_data:
            return
        
        okpd_code = okpd_data.get('sub_code') or okpd_data.get('main_code', '')
        if not okpd_code:
            QMessageBox.warning(self, "Ошибка", "Не удалось определить код ОКПД")
            return
        
        # Добавляем в БД
        success = self.tender_repo.add_user_okpd_code(
            user_id=self.current_user_id,
            okpd_code=okpd_code,
            name=okpd_data.get('name')
        )
        
        if success:
            QMessageBox.information(self, "Успех", f"Код ОКПД {okpd_code} добавлен")
            self.load_user_okpd_codes()  # Обновляем список добавленных
        else:
            QMessageBox.warning(self, "Предупреждение", "Код ОКПД уже был добавлен ранее")
    
    def load_user_okpd_codes(self):
        """Загрузка и отображение добавленных ОКПД пользователя"""
        if not self.tender_repo:
            return
        
        # Очищаем контейнер
        while self.added_okpd_layout.count():
            item = self.added_okpd_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Загружаем ОКПД пользователя
        user_okpd = self.tender_repo.get_user_okpd_codes(self.current_user_id)
        
        if not user_okpd:
            no_data_label = QLabel("Нет добавленных кодов ОКПД")
            apply_label_style(no_data_label, 'normal')
            apply_text_style_light_italic(no_data_label)
            self.added_okpd_layout.addWidget(no_data_label)
            return
        
        # Создаем лейблы для каждого ОКПД
        for okpd in user_okpd:
            okpd_frame = QFrame()
            okpd_frame.setMinimumHeight(60)  # Увеличена минимальная высота элемента
            okpd_frame.setStyleSheet(f"""
                QFrame {{
                    background: {COLORS['secondary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: {SIZES['border_radius_normal']}px;
                    padding: 12px;
                }}
            """)
            
            okpd_item_layout = QHBoxLayout(okpd_frame)
            okpd_item_layout.setContentsMargins(12, 10, 12, 10)  # Увеличены отступы
            
            code = okpd.get('okpd_code', '')
            name = okpd.get('okpd_name') or okpd.get('name', 'Без названия')
            
            label_text = f"{code} - {name[:60]}" if name else code
            okpd_label = QLabel(label_text)
            apply_label_style(okpd_label, 'normal')
            okpd_label.setWordWrap(True)  # Перенос текста на новую строку
            okpd_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {FONT_SIZES['normal']};
                    padding: 5px;
                    min-height: 40px;
                }}
            """)
            okpd_item_layout.addWidget(okpd_label)
            
            okpd_item_layout.addStretch()
            
            # Кнопка удаления
            btn_remove = QPushButton("✕")
            btn_remove.setFixedSize(30, 30)
            apply_button_style(btn_remove, 'outline')
            btn_remove.setStyleSheet(f"""
                QPushButton {{
                    border-radius: 15px;
                    font-weight: bold;
                }}
            """)
            btn_remove.clicked.connect(
                lambda checked, okpd_id=okpd['id']: self.handle_remove_okpd(okpd_id)
            )
            okpd_item_layout.addWidget(btn_remove)
            
            self.added_okpd_layout.addWidget(okpd_frame)
    
    def handle_remove_okpd(self, okpd_id: int):
        """Обработка удаления ОКПД"""
        if not self.tender_repo:
            return
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить этот код ОКПД?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.tender_repo.remove_user_okpd_code(self.current_user_id, okpd_id)
            if success:
                QMessageBox.information(self, "Успех", "Код ОКПД удален")
                self.load_user_okpd_codes()  # Обновляем список
    
    def load_regions(self):
        """Загрузка списка регионов в выпадающий список"""
        if not self.tender_repo:
            logger.warning("Репозиторий торгов не инициализирован, регионы не загружены")
            return
        
        try:
            if not hasattr(self, 'region_combo') or self.region_combo is None:
                logger.warning("region_combo не инициализирован")
                return
            
            self.region_combo.clear()
            
            # Добавляем опцию "Все регионы"
            self.region_combo.addItem("Все регионы", None)
            
            # Загружаем регионы из БД
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
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке регионов: {e}")
            # Добавляем хотя бы опцию "Все регионы" в случае ошибки
            if hasattr(self, 'region_combo') and self.region_combo:
                self.region_combo.clear()
                self.region_combo.addItem("Все регионы", None)
    
    def on_region_changed(self, index: int):
        """Обработка изменения выбранного региона"""
        # Проверяем, что все элементы инициализированы
        if not hasattr(self, 'okpd_search_input') or self.okpd_search_input is None:
            return
        
        # Перезагружаем список ОКПД с учетом нового региона
        search_text = self.okpd_search_input.text() if self.okpd_search_input.text() else None
        self.load_okpd_codes(search_text)
    
    def load_user_stop_words(self):
        """Загрузка и отображение стоп-слов пользователя"""
        if not self.tender_repo:
            return
        
        # Очищаем контейнер
        while self.stop_words_layout.count():
            item = self.stop_words_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Загружаем стоп-слова пользователя
        user_stop_words = self.tender_repo.get_user_stop_words(self.current_user_id)
        
        if not user_stop_words:
            no_data_label = QLabel("Нет добавленных стоп-слов")
            apply_label_style(no_data_label, 'normal')
            apply_text_style_light_italic(no_data_label)
            self.stop_words_layout.addWidget(no_data_label)
            return
        
        # Создаем фреймы для каждого стоп-слова
        for stop_word_data in user_stop_words:
            stop_word_frame = QFrame()
            stop_word_frame.setMinimumHeight(50)
            stop_word_frame.setStyleSheet(f"""
                QFrame {{
                    background: {COLORS['secondary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: {SIZES['border_radius_normal']}px;
                    padding: 12px;
                }}
            """)
            
            stop_word_item_layout = QHBoxLayout(stop_word_frame)
            stop_word_item_layout.setContentsMargins(12, 8, 12, 8)
            
            stop_word_text = stop_word_data.get('stop_word', '')
            stop_word_label = QLabel(stop_word_text)
            apply_label_style(stop_word_label, 'normal')
            stop_word_label.setWordWrap(True)
            stop_word_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {FONT_SIZES['normal']};
                    padding: 5px;
                    min-height: 30px;
                }}
            """)
            stop_word_item_layout.addWidget(stop_word_label)
            
            stop_word_item_layout.addStretch()
            
            # Кнопка удаления
            btn_remove = QPushButton("✕")
            btn_remove.setFixedSize(30, 30)
            apply_button_style(btn_remove, 'outline')
            btn_remove.setStyleSheet(f"""
                QPushButton {{
                    border-radius: 15px;
                    font-weight: bold;
                }}
            """)
            btn_remove.clicked.connect(
                lambda checked, word_id=stop_word_data['id']: self.handle_remove_stop_word(word_id)
            )
            stop_word_item_layout.addWidget(btn_remove)
            
            self.stop_words_layout.addWidget(stop_word_frame)
    
    def handle_add_stop_words(self):
        """Обработка добавления стоп-слов"""
        if not self.tender_repo:
            QMessageBox.warning(self, "Ошибка", "Нет подключения к базе данных")
            return
        
        input_text = self.stop_words_input.text().strip()
        if not input_text:
            QMessageBox.warning(self, "Предупреждение", "Введите стоп-слово или несколько слов")
            return
        
        # Разбиваем введенный текст на отдельные слова
        # Поддерживаем разделение через запятую, точку с запятой или перенос строки
        # Разбиваем по запятой, точке с запятой или переносу строки
        words = re.split(r'[,;\n\r]+', input_text)
        # Очищаем каждое слово от пробелов и фильтруем пустые
        words = [word.strip() for word in words if word.strip()]
        
        if not words:
            QMessageBox.warning(self, "Предупреждение", "Не удалось извлечь стоп-слова из введенного текста")
            return
        
        # Добавляем стоп-слова в БД
        result = self.tender_repo.add_user_stop_words(
            user_id=self.current_user_id,
            stop_words=words
        )
        
        # Формируем сообщение о результате
        message_parts = []
        if result['added'] > 0:
            message_parts.append(f"Добавлено: {result['added']}")
        if result['skipped'] > 0:
            message_parts.append(f"Пропущено (уже существуют): {result['skipped']}")
        if result['errors']:
            message_parts.append(f"Ошибок: {len(result['errors'])}")
        
        if message_parts:
            message = "\n".join(message_parts)
            if result['added'] > 0:
                QMessageBox.information(self, "Результат", message)
            else:
                QMessageBox.warning(self, "Результат", message)
        
        # Очищаем поле ввода
        self.stop_words_input.clear()
        
        # Обновляем список стоп-слов
        self.load_user_stop_words()
    
    def handle_remove_stop_word(self, stop_word_id: int):
        """Обработка удаления стоп-слова"""
        if not self.tender_repo:
            return
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить это стоп-слово?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.tender_repo.remove_user_stop_word(self.current_user_id, stop_word_id)
            if success:
                QMessageBox.information(self, "Успех", "Стоп-слово удалено")
                self.load_user_stop_words()  # Обновляем список
