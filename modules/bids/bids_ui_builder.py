"""
Построитель UI для BidsWidget

Отвечает за создание и настройку пользовательского интерфейса виджета закупок.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QFrame, QPushButton
from modules.styles.general_styles import (
    apply_label_style, apply_frame_style, apply_button_style,
    apply_tab_style, apply_text_style_light_italic
)
from modules.bids.tender_list_widget import TenderListWidget
from modules.bids.bids_settings_tab import BidsSettingsTab


class BidsUIBuilder:
    """Построитель UI для виджета закупок"""
    
    def __init__(
        self,
        parent_widget,
        tender_repo,
        user_id,
        search_params_cache,
        document_search_service,
        tender_match_repo,
        tender_match_repository
    ):
        """
        Инициализация построителя UI
        
        Args:
            parent_widget: Родительский виджет
            tender_repo: Репозиторий закупок
            user_id: ID пользователя
            search_params_cache: Кэш параметров поиска
            document_search_service: Сервис поиска документов
            tender_match_repo: Репозиторий результатов поиска
            tender_match_repository: Алиас для репозитория результатов поиска
        """
        self.parent_widget = parent_widget
        self.tender_repo = tender_repo
        self.user_id = user_id
        self.search_params_cache = search_params_cache
        self.document_search_service = document_search_service
        self.tender_match_repo = tender_match_repo
        self.tender_match_repository = tender_match_repository
    
    def build_ui(self):
        """
        Построение пользовательского интерфейса
        
        Returns:
            tuple: (analyze_button, analyze_all_button, refresh_button, tabs, settings_tab,
                   tenders_44fz_widget, tenders_223fz_widget, won_tenders_44fz_widget, won_tenders_223fz_widget)
        """
        # Основной layout
        main_layout = QVBoxLayout(self.parent_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок раздела
        header_frame = QFrame()
        apply_frame_style(header_frame, 'content')
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Заголовок и кнопки в одной строке
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("📈 Закупки")
        apply_label_style(title, 'h1')
        header_row.addWidget(title)
        
        header_row.addStretch()
        
        # Кнопка анализа документации для выбранных закупок
        analyze_button = QPushButton("📄 Анализ выбранных")
        apply_button_style(analyze_button, 'primary')
        analyze_button.setToolTip("Запустить анализ документации для выбранных закупок")
        analyze_button.setEnabled(False)
        header_row.addWidget(analyze_button)
        
        # Кнопка анализа всех закупок
        analyze_all_button = QPushButton("📊 Анализировать все")
        apply_button_style(analyze_all_button, 'secondary')
        analyze_all_button.setToolTip("Запустить анализ документации для всех закупок (приоритетные обрабатываются первыми)")
        header_row.addWidget(analyze_all_button)
        
        # Кнопка обновления ленты
        refresh_button = QPushButton("🔄 Обновить ленту")
        apply_button_style(refresh_button, 'outline')
        refresh_button.setToolTip("Обновить статусы обработки документов для всех закупок")
        header_row.addWidget(refresh_button)
        
        header_layout.addLayout(header_row)
        main_layout.addWidget(header_frame)
        
        # Вкладки для различных разделов закупок
        tabs = QTabWidget()
        apply_tab_style(tabs)
        
        # Вкладка "Настройки"
        settings_tab = BidsSettingsTab(
            tender_repo=self.tender_repo,
            user_id=self.user_id,
            search_params_cache=self.search_params_cache,
            parent_widget=self.parent_widget
        )
        tabs.addTab(settings_tab, "Настройки")
        
        # Вкладка "Новые закупки 44ФЗ"
        tenders_44fz_widget = TenderListWidget(
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repo,
        )
        tabs.addTab(tenders_44fz_widget, "Новые закупки 44ФЗ")
        
        # Вкладка "Новые закупки 223ФЗ"
        tenders_223fz_widget = TenderListWidget(
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repo,
        )
        tabs.addTab(tenders_223fz_widget, "Новые закупки 223ФЗ")
        
        # Вкладка "Разыгранные закупки 44ФЗ"
        won_tenders_44fz_widget = TenderListWidget(
            parent=self.parent_widget,
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repository,
        )
        tabs.addTab(won_tenders_44fz_widget, "Разыгранные закупки 44ФЗ")
        
        # Вкладка "Разыгранные закупки 223ФЗ"
        won_tenders_223fz_widget = TenderListWidget(
            parent=self.parent_widget,
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repository,
        )
        tabs.addTab(won_tenders_223fz_widget, "Разыгранные закупки 223ФЗ")
        
        # Вкладка "Работа комиссии 44 ФЗ"
        commission_tenders_44fz_widget = TenderListWidget(
            parent=self.parent_widget,
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repository,
        )
        tabs.addTab(commission_tenders_44fz_widget, "Работа комиссии 44 ФЗ")
        
        # Вкладка "В работе"
        in_work_tab = QWidget()
        in_work_layout = QVBoxLayout(in_work_tab)
        in_work_layout.setContentsMargins(20, 20, 20, 20)
        
        in_work_label = QLabel("Закупки в работе")
        apply_label_style(in_work_label, 'h2')
        in_work_layout.addWidget(in_work_label)
        
        in_work_info = QLabel("Раздел закупок в работе будет реализован позже")
        apply_label_style(in_work_info, 'normal')
        apply_text_style_light_italic(in_work_info)
        in_work_layout.addWidget(in_work_info)
        in_work_layout.addStretch()
        
        tabs.addTab(in_work_tab, "В работе")
        
        # Добавляем вкладки в основной layout
        main_layout.addWidget(tabs)
        
        return (
            analyze_button, analyze_all_button, refresh_button, tabs, settings_tab,
            tenders_44fz_widget, tenders_223fz_widget, won_tenders_44fz_widget, won_tenders_223fz_widget,
            commission_tenders_44fz_widget
        )

