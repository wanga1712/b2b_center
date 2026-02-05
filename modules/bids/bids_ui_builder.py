"""
MODULE: modules.bids.bids_ui_builder
RESPONSIBILITY: Construct the UI layout for BidsWidget.
ALLOWED: PyQt5, modules.styles, modules.bids.*.
FORBIDDEN: Processing logic.
ERRORS: None.

Построитель UI для BidsWidget

Отвечает за создание и настройку пользовательского интерфейса виджета закупок.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QFrame, QPushButton, QStackedWidget
from modules.styles.general_styles import (
    apply_label_style, apply_frame_style, apply_button_style,
    apply_tab_style, apply_text_style_light_italic, COLORS
)
from modules.bids.tender_list_widget import TenderListWidget
from modules.bids.bids_settings_tab import BidsSettingsTab
from modules.bids.bids_dashboard import BidsDashboard


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
            tuple: (analyze_button, analyze_all_button, refresh_button, stack_widget, dashboard,
                   settings_tab, tenders_44fz_widget, tenders_223fz_widget, ...)
        """
        # Основной layout
        main_layout = QVBoxLayout(self.parent_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Stacked widget для переключения между dashboard и разделами
        stack_widget = QStackedWidget()
        # Исправление: используем 'secondary' вместо несуществующего 'background'
        background_color = COLORS.get('background', COLORS.get('secondary', '#F5F5F5'))
        stack_widget.setStyleSheet(f"QStackedWidget {{ background: {background_color}; }}")
        
        # === Dashboard (начальная страница) ===
        dashboard = BidsDashboard()
        stack_widget.addWidget(dashboard)  # index 0
        
        # === Контейнер для разделов с верхней панелью ===
        sections_container = QWidget()
        sections_layout = QVBoxLayout(sections_container)
        sections_layout.setSpacing(0)
        sections_layout.setContentsMargins(0, 0, 0, 0)
        
        # Верхняя панель для разделов (скрыта на dashboard)
        header_frame = QFrame()
        apply_frame_style(header_frame, 'content')
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Кнопка "Назад к Dashboard" + заголовок + кнопки действий
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        
        # Кнопка назад
        back_button = QPushButton("🏠 Dashboard")
        apply_button_style(back_button, 'outline')
        back_button.setToolTip("Вернуться на главную страницу")
        header_row.addWidget(back_button)
        
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
        sections_layout.addWidget(header_frame)
        
        # Вкладки для различных разделов закупок
        tabs = QTabWidget()
        apply_tab_style(tabs)
        
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
        
        # Добавляем вкладки в sections_layout
        sections_layout.addWidget(tabs)
        stack_widget.addWidget(sections_container)  # index 1
        
        # === Настройки (отдельная страница) ===
        settings_tab = BidsSettingsTab(
            tender_repo=self.tender_repo,
            user_id=self.user_id,
            search_params_cache=self.search_params_cache,
            parent_widget=self.parent_widget
        )
        stack_widget.addWidget(settings_tab)  # index 2
        
        # Добавляем stack_widget в основной layout
        main_layout.addWidget(stack_widget)
        
        # === Подключение сигналов ===
        # Dashboard -> разделы
        dashboard.section_selected.connect(lambda section_id: self._on_section_selected(stack_widget, tabs, section_id))
        dashboard.settings_clicked.connect(lambda: stack_widget.setCurrentIndex(2))
        
        # Кнопка "Назад" -> Dashboard
        back_button.clicked.connect(lambda: stack_widget.setCurrentIndex(0))
        
        # Сохраняем ссылки для дальнейшего использования
        self.parent_widget._dashboard = dashboard
        self.parent_widget._stack_widget = stack_widget
        self.parent_widget._tabs = tabs
        self.parent_widget._back_button = back_button
        return (
            analyze_button, analyze_all_button, refresh_button, stack_widget, dashboard,
            settings_tab, tenders_44fz_widget, tenders_223fz_widget, won_tenders_44fz_widget,
            won_tenders_223fz_widget, commission_tenders_44fz_widget, back_button, tabs
        )
    
    def _on_section_selected(self, stack_widget: QStackedWidget, tabs: QTabWidget, section_id: str):
        """Обработка выбора раздела на dashboard."""
        # Переключаемся на страницу с разделами
        stack_widget.setCurrentIndex(1)
        
        # Маппинг section_id на индекс вкладки
        section_map = {
            "purchases_44fz_new": 0,
            "purchases_223fz_new": 1,
            "purchases_44fz_won": 2,
            "purchases_223fz_won": 3,
            "purchases_44fz_commission": 4,
            "purchases_in_work": 5,
        }
        
        tab_index = section_map.get(section_id, 0)
        tabs.setCurrentIndex(tab_index)

