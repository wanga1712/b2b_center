"""
Виджет подменю для раздела Закупки

Отображает подразделы закупок с иконками и счетчиками.
Включает встроенные настройки под иконками.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QPixmap, QMovie
from pathlib import Path
from typing import Optional
from loguru import logger

from modules.styles.general_styles import (
    apply_label_style, COLORS, SIZES
)
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
        self.item_cards: Dict[str, FolderCard] = {}
        self._counts_loaded = False  # Флаг, что счетчики загружены
        self.settings_tab = None
        self.init_ui()
        self.load_submenu_items()
        # НЕ загружаем счетчики при инициализации - только после нажатия "Показать тендеры"
    
    def init_ui(self):
        """Инициализация интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Заголовок с кнопкой "Назад"
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)
        
        # Кнопка "Назад"
        from PyQt5.QtWidgets import QPushButton
        from modules.styles.general_styles import apply_button_style
        back_button = QPushButton("← Назад к разделам CRM")
        apply_button_style(back_button, 'outline')
        back_button.clicked.connect(self.on_back_clicked)
        header_layout.addWidget(back_button)
        
        # Заголовок
        header = QLabel("📊 Закупки")
        apply_label_style(header, 'h1')
        header.setStyleSheet(f"color: {COLORS['primary']}; margin-bottom: {SIZES['padding_large']}px;")
        header_layout.addWidget(header)
        
        main_layout.addLayout(header_layout)
        
        # Область прокрутки для элементов подменю
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
        
        # Контейнер для элементов подменю с grid layout
        items_container = QWidget()
        self.items_layout = QGridLayout(items_container)
        self.items_layout.setSpacing(20)
        self.items_layout.setContentsMargins(10, 10, 10, 10)
        # Градиентный фон за карточками
        items_container.setStyleSheet("""
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
        
        scroll_area.setWidget(items_container)
        main_layout.addWidget(scroll_area)
        
        # Добавляем виджет настроек под иконками (ВСЕГДА ВИДИМЫЙ, вне ScrollArea)
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
        """Отображение элементов подменю в grid layout"""
        # Очищаем существующие элементы
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Добавляем элементы в grid (по 4 в ряд)
        row = 0
        col = 0
        max_cols = 4
        
        for item_data in items_data:
            item_card = FolderCard(
                folder_id=item_data['id'],
                name=item_data['name'],
                icon='📋',  # Fallback
                description=None,
                count=item_data.get('count'),
                icon_path=str(item_data['icon_path']) if item_data['icon_path'].exists() else None
            )
            item_card.clicked.connect(self.on_submenu_item_clicked)
            self.item_cards[item_data['id']] = item_card
            
            self.items_layout.addWidget(item_card, row, col)
            
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
            # Обновляем счетчики в карточках
            for item_id, count in counts.items():
                if item_id in self.item_cards:
                    self.item_cards[item_id].update_count(count)
            
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

