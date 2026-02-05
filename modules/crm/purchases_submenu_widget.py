"""
MODULE: modules.crm.purchases_submenu_widget
RESPONSIBILITY: Display purchases submenu with stats and filter settings.
ALLOWED: PyQt5, loguru, pathlib, modules.styles.*, modules.bids.*, modules.crm.folder_card, modules.crm.purchases_counts_service.
FORBIDDEN: Direct SQL queries (use repositories).
ERRORS: None.

Виджет подменю для раздела Закупки (Salesforce/Windows 11 style)

Отображает подразделы закупок с плитками в стиле Windows 11 и статистикой в стиле Salesforce.
Включает встроенные настройки внизу.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QScrollArea, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QPixmap, QMovie, QFont
from pathlib import Path
from typing import Optional
from loguru import logger

from modules.styles.general_styles import (
    apply_label_style, apply_button_style, COLORS, SIZES, FONT_SIZES
)
from modules.bids.bids_dashboard import BidsTile
from modules.bids.salesforce_stats_widgets import SalesforceStatsCard, SalesforceGaugeCard
from modules.crm.folder_card import FolderCard
from modules.crm.purchases_counts_service import PurchasesCountsService
from typing import Dict, Optional


class PurchasesSubmenuWidget(QWidget):
    """
    Виджет подменю для раздела Закупки
    
    Отображает подразделы: новые/завершенные 44ФЗ/223ФЗ.
    Включает встроенные настройки под иконками.
    """
    
    submenu_item_clicked = pyqtSignal(str)  # Сигнал при клике на элемент подменю
    
    def __init__(
        self,
        counts_service: Optional[PurchasesCountsService] = None,
        tender_repo=None,
        user_id: int = 1,
        search_params_cache=None,
        parent=None
    ):
        """
        Инициализация виджета подменю
        
        Args:
            counts_service: Сервис для подсчета закупок
            tender_repo: Репозиторий закупок (для настроек)
            user_id: ID пользователя (для настроек)
            search_params_cache: Кэш параметров поиска (для настроек)
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.counts_service = counts_service
        self.tender_repo = tender_repo
        self.user_id = user_id
        self.search_params_cache = search_params_cache
        self.item_tiles: Dict[str, BidsTile] = {}  # Используем BidsTile вместо FolderCard
        self.stats_cards: list = []
        self._counts_loaded = False  # Флаг, что счетчики загружены
        self.settings_tab = None
        self.init_ui()
        self.load_submenu_items()
        # НЕ загружаем счетчики при инициализации - только после нажатия "Показать тендеры"
    
    def init_ui(self):
        """Инициализация интерфейса в стиле Salesforce/Windows 11"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Скроллируемая область
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(
            f"QScrollArea {{ border: none; background: {COLORS.get('background', COLORS['secondary'])}; }}"
        )
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(30)
        
        # Заголовок с кнопкой "Назад"
        header_layout = self._create_header()
        container_layout.addLayout(header_layout)
        
        # Статистика (Salesforce style)
        stats_layout = self._create_stats_section()
        container_layout.addLayout(stats_layout)
        
        # Плитки разделов (Windows 11 style)
        tiles_layout = self._create_tiles_section()
        container_layout.addLayout(tiles_layout)
        
        container_layout.addStretch()
        
        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)
        
        # Добавляем виджет настроек внизу (ВСЕГДА ВИДИМЫЙ, вне ScrollArea)
        logger.info(f"Проверка условий для отображения настроек: tender_repo={self.tender_repo is not None}, search_params_cache={self.search_params_cache is not None}")
        if self.tender_repo and self.search_params_cache:
            logger.info("Условия выполнены, создаем виджет настроек")
            try:
                from modules.bids.bids_settings_tab import BidsSettingsTab
                
                # Добавляем разделитель перед настройками
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setStyleSheet(f"QFrame {{ color: {COLORS['border']}; margin: 20px 0; }}")
                main_layout.addWidget(separator)
                
                # Заголовок для настроек
                settings_header = QLabel("⚙️ Настройки поиска закупок")
                apply_label_style(settings_header, 'h2')
                settings_header.setStyleSheet(f"color: {COLORS['primary']}; margin-top: {SIZES['padding_large']}px;")
                main_layout.addWidget(settings_header)
                
                # Создаем виджет настроек
                self.settings_tab = BidsSettingsTab(
                    tender_repo=self.tender_repo,
                    user_id=self.user_id,
                    search_params_cache=self.search_params_cache,
                    parent_widget=self  # Передаем self как parent_widget для обратных вызовов
                )
                
                # Убеждаемся, что виджет настроек видим
                self.settings_tab.setVisible(True)
                
                # Добавляем виджет настроек в layout
                main_layout.addWidget(self.settings_tab)
                logger.info("Виджет настроек успешно добавлен в layout и установлен как видимый")
            except Exception as e:
                logger.error(f"Ошибка при создании виджета настроек: {e}", exc_info=True)
        else:
            logger.warning(f"Настройки не отображаются: tender_repo={self.tender_repo is not None}, search_params_cache={self.search_params_cache is not None}")
    
    def _create_header(self) -> QVBoxLayout:
        """Создание заголовка с кнопкой Назад"""
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)
        
        # Кнопка "Назад"
        back_button = QPushButton("← Назад к разделам CRM")
        apply_button_style(back_button, 'outline')
        back_button.clicked.connect(self.on_back_clicked)
        header_layout.addWidget(back_button)
        
        # Заголовок
        title_label = QLabel("📈 Управление закупками")
        title_label.setStyleSheet(
            f"font-size: {FONT_SIZES['h1']}; font-weight: bold; color: {COLORS['text_dark']};"
        )
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Закупки 44ФЗ и 223ФЗ • Анализ документации • Управление")
        subtitle_label.setStyleSheet(
            f"font-size: {FONT_SIZES['normal']}; color: {COLORS['text_light']};"
        )
        header_layout.addWidget(subtitle_label)
        
        return header_layout
    
    def _create_stats_section(self) -> QHBoxLayout:
        """Создание секции статистики (Salesforce style с прогресс-индикаторами)"""
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        # Карточки статистики с прогресс-барами
        stats_data = [
            ("Всего закупок", 0, 100, "📊", COLORS['primary'], True),  # value, max, icon, color, show_progress
            ("В работе", 0, 100, "⚡", "#ffc107", True),
            ("Обработано", 0, 100, "✓", "#28a745", True),
            ("Новых", 0, 50, "🔔", "#17a2b8", True),
        ]
        
        for title, value, max_val, icon, color, show_prog in stats_data:
            card = SalesforceStatsCard(
                title=title,
                value=value,
                max_value=max_val,
                icon=icon,
                color=color,
                show_progress=show_prog
            )
            self.stats_cards.append(card)
            stats_layout.addWidget(card)
        
        stats_layout.addStretch()
        
        return stats_layout
    
    def _create_tiles_section(self) -> QVBoxLayout:
        """Создание секции с папками разделов (Windows style)"""
        tiles_layout = QVBoxLayout()
        tiles_layout.setSpacing(20)
        
        # Заголовок секции
        section_label = QLabel("📁 Разделы закупок")
        section_label.setStyleSheet(
            f"font-size: {FONT_SIZES['h2']}; font-weight: bold; color: {COLORS['text_dark']};"
        )
        tiles_layout.addWidget(section_label)
        
        # Сетка для папок (будем использовать FolderCard)
        self.items_layout = QGridLayout()
        self.items_layout.setSpacing(20)
        
        tiles_layout.addLayout(self.items_layout)
        
        return tiles_layout
    
    def load_submenu_items(self):
        """Загрузка элементов подменю"""
        submenu_dir = Path(__file__).parent.parent.parent / 'img' / 'submenu_purchaiser'
        
        # Определяем структуру подменю - отдельные разделы для 44ФЗ и 223ФЗ
        submenu_items = [
            {
                'id': 'purchases_44fz_new',
                'name': 'Новые закупки по 44 ФЗ',
                'icon_path': submenu_dir / 'new purchases.gif',
                'count': None,  # Будет загружено после нажатия "Показать тендеры"
            },
            {
                'id': 'purchases_44fz_won',
                'name': 'Разыгранные закупки по 44 ФЗ',
                'icon_path': submenu_dir / 'completed purchases.gif',
                'count': None,  # Будет загружено после нажатия "Показать тендеры"
            },
            {
                'id': 'purchases_44fz_commission',
                'name': 'Работа комиссии 44 ФЗ',
                'icon_path': submenu_dir / 'commission_work.gif' if (submenu_dir / 'commission_work.gif').exists() else submenu_dir / 'new purchases.gif',
                'count': None,  # Будет загружено после нажатия "Показать тендеры"
            },
            {
                'id': 'purchases_223fz_new',
                'name': 'Новые закупки по 223 ФЗ',
                'icon_path': submenu_dir / 'new purchases.gif',
                'count': None,  # Будет загружено после нажатия "Показать тендеры"
            },
            {
                'id': 'purchases_223fz_won',
                'name': 'Разыгранные закупки по 223 ФЗ',
                'icon_path': submenu_dir / 'completed purchases.gif',
                'count': None,  # Будет загружено после нажатия "Показать тендеры"
            },
        ]
        
        # Отображаем элементы подменю
        self.display_submenu_items(submenu_items)
    
    def display_submenu_items(self, items_data: list):
        """Отображение элементов подменю как папок Windows style"""
        # Очищаем существующие элементы
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Добавляем элементы как папки (по 4 в ряд, как в Windows)
        row = 0
        col = 0
        max_cols = 4
        
        for item_data in items_data:
            section_id = item_data['id']
            
            # Создаем карточку-папку в стиле Windows
            folder_card = FolderCard(
                folder_id=section_id,
                name=item_data['name'],
                icon='📁',  # Иконка папки
                description=None,
                count=item_data.get('count'),
                icon_path=str(item_data['icon_path']) if item_data.get('icon_path') and item_data['icon_path'].exists() else None
            )
            folder_card.clicked.connect(self.on_submenu_item_clicked)
            self.item_tiles[section_id] = folder_card
            
            self.items_layout.addWidget(folder_card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def on_submenu_item_clicked(self, item_id: str):
        """Обработка клика на элемент подменю"""
        logger.info(f"Клик на элемент подменю закупок: {item_id}")
        self.submenu_item_clicked.emit(item_id)
    
    def on_back_clicked(self):
        """Обработка клика на кнопку 'Назад'"""
        self.submenu_item_clicked.emit('back_to_crm')
    
    def update_counts(self, counts: Dict[str, int]):
        """
        Обновление счетчиков из переданного словаря
        
        Args:
            counts: Словарь с количеством закупок {item_id: count}
        """
        try:
            # Обновляем счетчики в папках (FolderCard)
            for item_id, count in counts.items():
                if item_id in self.item_tiles:
                    self.item_tiles[item_id].update_count(count)
            
            # Обновляем статистику (Salesforce cards с прогресс-барами)
            total = sum(counts.values())
            if len(self.stats_cards) >= 4:
                # Обновляем значения в карточках
                self.stats_cards[0].update_value(total, max_value=total if total > 0 else 100)  # Всего
                # Остальные карточки можно обновить по необходимости
                # self.stats_cards[1].update_value(...)  # В работе
                # self.stats_cards[2].update_value(...)  # Обработано
                # self.stats_cards[3].update_value(...)  # Новых
            
            logger.info(f"Счетчики закупок обновлены: {counts}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении счетчиков закупок: {e}")
    
    def handle_show_tenders(self):
        """
        Обработка нажатия кнопки 'Показать тендеры' в настройках
        
        Обновляет счетчики на иконках после настройки фильтров.
        """
        if not self.counts_service:
            logger.warning("Сервис подсчета закупок не инициализирован")
            return
        
        # Получаем фильтры из настроек
        category_id = None
        user_okpd_codes = None
        user_stop_words = None
        region_id = None
        
        if self.settings_tab:
            # Получаем категорию
            category_filter_combo = getattr(self.settings_tab, 'category_filter_combo', None)
            if category_filter_combo:
                category_id = category_filter_combo.currentData()
            
            # Получаем регион
            region_combo = getattr(self.settings_tab, 'region_combo', None)
            if region_combo:
                region_data = region_combo.currentData()
                if region_data:
                    region_id = region_data.get('id')
            
            # Получаем ОКПД коды из категории (если выбрана) или все ОКПД пользователя
            try:
                if category_id:
                    # Если выбрана категория - получаем ОКПД коды ТОЛЬКО из этой категории
                    user_okpd_codes = self.tender_repo.get_okpd_codes_by_category(self.user_id, category_id)
                    logger.info(f"Используются ОКПД коды из категории {category_id}: {len(user_okpd_codes)} кодов")
                else:
                    # Если категория не выбрана - получаем все ОКПД пользователя
                    user_okpd_list = self.tender_repo.get_user_okpd_codes(self.user_id) if self.tender_repo else None
                    if user_okpd_list:
                        user_okpd_codes = [item.get('okpd_code') for item in user_okpd_list if item.get('okpd_code')]
                    else:
                        user_okpd_codes = []
                
                # Получаем стоп-слова
                user_stop_words_list = self.tender_repo.get_user_stop_words(self.user_id) if self.tender_repo else None
                if user_stop_words_list:
                    user_stop_words = [item.get('stop_word') for item in user_stop_words_list if item.get('stop_word')]
                else:
                    user_stop_words = []
            except Exception as e:
                logger.error(f"Ошибка получения фильтров пользователя: {e}")
                user_okpd_codes = []
                user_stop_words = []
        
        # Обновляем счетчики с учетом фильтров
        counts = self.counts_service.get_counts(
            category_id=category_id,
            user_okpd_codes=user_okpd_codes,
            user_stop_words=user_stop_words,
            region_id=region_id
        )
        self.update_counts(counts)
        
        logger.info("Счетчики закупок обновлены после настройки фильтров")

