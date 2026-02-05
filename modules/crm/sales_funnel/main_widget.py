"""
MODULE: modules.crm.sales_funnel.main_widget
RESPONSIBILITY: Main widget for Sales Funnel section (Dashboard + Tabs).
ALLOWED: PyQt5, loguru, modules.styles.*, modules.crm.sales_funnel.*, modules.bids.*.
FORBIDDEN: Direct SQL queries (use repositories).
ERRORS: None.

Главный виджет воронок продаж с Dashboard в стиле Salesforce
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QStackedWidget, QTabWidget, QFrame
)
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from loguru import logger

from modules.styles.general_styles import (
    apply_label_style, apply_button_style, COLORS, SIZES, FONT_SIZES
)
from modules.crm.sales_funnel.models import PipelineType
from modules.crm.sales_funnel.deal_repository import DealRepository
from modules.crm.sales_funnel.pipeline_repository import PipelineRepository
from modules.crm.sales_funnel.funnel_widget import SalesFunnelWidget
from modules.bids.salesforce_stats_widgets import SalesforceStatsCard
from modules.bids.bids_dashboard import BidsTile


class SalesFunnelMainWidget(QWidget):
    """
    Главный виджет воронок продаж с Dashboard в стиле Salesforce
    
    Структура:
    - Dashboard с плитками воронок и статистикой (Salesforce style)
    - Вкладки для каждой воронки (канбан-доски)
    - Настройки
    """
    
    def __init__(self, tender_db_manager, user_id: int = 1, parent=None):
        """
        Args:
            tender_db_manager: Менеджер БД tender_monitor
            user_id: ID пользователя
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.tender_db_manager = tender_db_manager
        self.user_id = user_id
        
        # Создаем репозитории, если передан tender_db_manager
        if tender_db_manager:
            try:
                self.deal_repo = DealRepository(tender_db_manager)
                self.pipeline_repo = PipelineRepository(tender_db_manager)
                logger.info("Репозитории инициализированы для SalesFunnelMainWidget")
            except Exception as e:
                logger.error(f"Ошибка создания репозиториев: {e}", exc_info=True)
                self.deal_repo = None
                self.pipeline_repo = None
        else:
            self.deal_repo = None
            self.pipeline_repo = None
            logger.warning("tender_db_manager не передан, репозитории не созданы")
        
        # UI элементы
        self.stack_widget = None
        self.dashboard = None
        self.tabs_widget = None
        self.stats_cards = []
        self.funnel_tiles = {}
        
        # Виджеты воронок
        self.participation_widget = None
        self.materials_widget = None
        self.subcontracting_widget = None
        
        self.init_ui()
        
        # Обновляем статистику только если есть подключение к БД
        if self.deal_repo:
            try:
                # #region agent log
                import json
                log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H1",
                        "location": "main_widget.py:__init__:before_update_stats",
                        "message": "Вызов update_stats из __init__",
                        "data": {
                            "deal_repo_exists": self.deal_repo is not None,
                            "stats_cards_count": len(self.stats_cards),
                            "funnel_tiles_count": len(self.funnel_tiles)
                        },
                        "timestamp": int(__import__("time").time() * 1000)
                    }, ensure_ascii=False) + "\n")
                # #endregion
                
                self.update_stats()
            except Exception as e:
                logger.error(f"Ошибка при обновлении статистики воронок: {e}", exc_info=True)
    
    def init_ui(self):
        """Инициализация интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # StackWidget для переключения между Dashboard и вкладками
        self.stack_widget = QStackedWidget()
        
        # Страница 0: Dashboard
        self.dashboard = self._create_dashboard()
        self.stack_widget.addWidget(self.dashboard)
        
        # Страница 1: Вкладки с воронками
        tabs_page = self._create_tabs_page()
        self.stack_widget.addWidget(tabs_page)
        
        # По умолчанию показываем Dashboard
        self.stack_widget.setCurrentIndex(0)
        
        # #region agent log
        import json
        log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "H5",
                "location": "main_widget.py:init_ui:after_setup",
                "message": "StackWidget настроен",
                "data": {
                    "stack_widget_pages": self.stack_widget.count(),
                    "current_index": self.stack_widget.currentIndex(),
                    "dashboard_is_widget": isinstance(self.dashboard, QWidget),
                    "dashboard_visible": self.dashboard.isVisible() if self.dashboard else False
                },
                "timestamp": int(__import__("time").time() * 1000)
            }, ensure_ascii=False) + "\n")
        # #endregion
        
        main_layout.addWidget(self.stack_widget)
    
    def _create_dashboard(self) -> QWidget:
        """Создание Dashboard с плитками и статистикой"""
        dashboard = QWidget()
        layout = QVBoxLayout(dashboard)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)
        
        # Заголовок
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        title = QLabel("📊 Воронка продаж")
        title.setStyleSheet(
            f"font-size: {FONT_SIZES['h1']}; font-weight: bold; color: {COLORS['text_dark']};"
        )
        header_layout.addWidget(title)
        
        subtitle = QLabel("Управление сделками • Участие • Материалы • Субподряд")
        subtitle.setStyleSheet(
            f"font-size: {FONT_SIZES['normal']}; color: {COLORS['text_light']};"
        )
        header_layout.addWidget(subtitle)
        
        layout.addLayout(header_layout)
        
        # Статистика (Salesforce style с прогресс-барами)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        stats_data = [
            ("Всего сделок", 0, 100, "📊", COLORS['primary'], True),
            ("В работе", 0, 50, "⚡", "#ffc107", True),
            ("Выиграно", 0, 50, "✓", "#28a745", True),
            ("Новых", 0, 20, "🔔", "#17a2b8", True),
        ]
        
        for title_text, value, max_val, icon, color, show_prog in stats_data:
            card = SalesforceStatsCard(
                title=title_text,
                value=value,
                max_value=max_val,
                icon=icon,
                color=color,
                show_progress=show_prog
            )
            self.stats_cards.append(card)
            stats_layout.addWidget(card)
        
        # #region agent log
        import json
        log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "H2",
                "location": "main_widget.py:_create_dashboard:after_create_stats",
                "message": "Карточки статистики созданы",
                "data": {"stats_cards_count": len(self.stats_cards)},
                "timestamp": int(__import__("time").time() * 1000)
            }, ensure_ascii=False) + "\n")
        # #endregion
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background: {COLORS['border']}; max-height: 2px;")
        layout.addWidget(separator)
        
        # Плитки воронок (3 воронки)
        tiles_label = QLabel("📂 Разделы воронок")
        tiles_label.setStyleSheet(
            f"font-size: {FONT_SIZES['h2']}; font-weight: bold; color: {COLORS['text_dark']};"
        )
        layout.addWidget(tiles_label)
        
        tiles_layout = QGridLayout()
        tiles_layout.setSpacing(20)
        tiles_layout.setContentsMargins(0, 10, 0, 10)
        
        # Данные плиток (id, title, icon, description, color)
        tiles_data = [
            ('participation', 'Участвовать', '🎯', 'Участие в тендерах', COLORS['primary']),
            ('materials', 'Материалы', '📦', 'Поставка материалов', '#17a2b8'),
            ('subcontracting', 'Субподряд', '🔧', 'Суб-подрядные работы', '#ffc107'),
        ]
        
        for idx, (tile_id, title_text, icon, description, color) in enumerate(tiles_data):
            tile = BidsTile(
                section_id=f'sales_funnel_{tile_id}',
                title=title_text,
                icon=icon,
                description=description,
                count=0,
                color=color
            )
            tile.clicked.connect(lambda checked, sid=tile_id: self._on_tile_clicked(sid))
            self.funnel_tiles[tile_id] = tile
            
            row = idx // 3
            col = idx % 3
            tiles_layout.addWidget(tile, row, col)
        
        # #region agent log
        import json
        log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "H3",
                "location": "main_widget.py:_create_dashboard:after_create_tiles",
                "message": "Плитки воронок созданы",
                "data": {
                    "funnel_tiles_count": len(self.funnel_tiles),
                    "funnel_tiles_keys": list(self.funnel_tiles.keys())
                },
                "timestamp": int(__import__("time").time() * 1000)
            }, ensure_ascii=False) + "\n")
        # #endregion
        
        layout.addLayout(tiles_layout)
        layout.addStretch()
        
        return dashboard
    
    def _create_tabs_page(self) -> QWidget:
        """Создание страницы с вкладками для воронок"""
        tabs_page = QWidget()
        layout = QVBoxLayout(tabs_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Кнопка "Назад"
        back_button = QPushButton("← Назад к Dashboard")
        apply_button_style(back_button, 'outline')
        back_button.clicked.connect(lambda: self.stack_widget.setCurrentIndex(0))
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(20, 20, 20, 10)
        header_layout.addWidget(back_button)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Вкладки для воронок
        self.tabs_widget = QTabWidget()
        
        # Создаем виджеты воронок только если есть подключение к БД
        if self.deal_repo and self.pipeline_repo:
            self.participation_widget = SalesFunnelWidget(
                pipeline_type=PipelineType.PARTICIPATION,
                pipeline_repo=self.pipeline_repo,
                deal_repo=self.deal_repo,
                user_id=self.user_id,
                tender_repo=None  # TODO: передать tender_repo для синхронизации
            )
            self.materials_widget = SalesFunnelWidget(
                pipeline_type=PipelineType.MATERIALS_SUPPLY,
                pipeline_repo=self.pipeline_repo,
                deal_repo=self.deal_repo,
                user_id=self.user_id,
                tender_repo=None
            )
            self.subcontracting_widget = SalesFunnelWidget(
                pipeline_type=PipelineType.SUBCONTRACTING,
                pipeline_repo=self.pipeline_repo,
                deal_repo=self.deal_repo,
                user_id=self.user_id,
                tender_repo=None
            )
            logger.info("Виджеты воронок созданы с канбан-досками")
        else:
            # Заглушки с сообщением, если БД не подключена
            from PyQt5.QtWidgets import QLabel
            from PyQt5.QtCore import Qt
            
            def create_placeholder(text: str) -> QWidget:
                widget = QWidget()
                layout = QVBoxLayout(widget)
                label = QLabel(text)
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet(f"color: {COLORS['text_light']}; font-size: 16px;")
                layout.addWidget(label)
                return widget
            
            self.participation_widget = create_placeholder("⚠️ Подключение к БД не установлено")
            self.materials_widget = create_placeholder("⚠️ Подключение к БД не установлено")
            self.subcontracting_widget = create_placeholder("⚠️ Подключение к БД не установлено")
            logger.warning("Виджеты воронок созданы как заглушки (нет БД)")
        
        # Добавляем вкладки
        self.tabs_widget.addTab(self.participation_widget, "🎯 Участвовать")
        self.tabs_widget.addTab(self.materials_widget, "📦 Материалы")
        self.tabs_widget.addTab(self.subcontracting_widget, "🔧 Субподряд")
        
        layout.addWidget(self.tabs_widget)
        
        return tabs_page
    
    def _on_tile_clicked(self, tile_id: str):
        """Обработка клика на плитку воронки"""
        logger.info(f"Клик на плитку воронки: {tile_id}")
        
        # Переключаемся на страницу с вкладками
        self.stack_widget.setCurrentIndex(1)
        
        # Переключаемся на нужную вкладку
        tab_map = {
            'participation': 0,
            'materials': 1,
            'subcontracting': 2,
        }
        
        tab_index = tab_map.get(tile_id)
        if tab_index is not None and self.tabs_widget:
            self.tabs_widget.setCurrentIndex(tab_index)
    
    def update_stats(self):
        """Обновление статистики"""
        try:
            logger.info("=== НАЧАЛО update_stats для SalesFunnelMainWidget ===")
            
            # Проверка наличия репозитория
            if not self.deal_repo:
                logger.warning("DealRepository не инициализирован, статистика не обновлена")
                return
            
            logger.info("DealRepository инициализирован, начинаем подсчет сделок")
            
            total_count = 0
            in_work_count = 0
            won_count = 0
            new_count = 0
            
            # Подсчет сделок по всем воронкам
            for pipeline_type in PipelineType:
                logger.debug(f"Загружаем сделки для {pipeline_type.value}")
                deals = self.deal_repo.get_deals(pipeline_type, self.user_id)
                count = len(deals)
                total_count += count
                
                logger.debug(f"Найдено сделок для {pipeline_type.value}: {count}")
                
                # Обновляем счетчик плитки
                tile_map = {
                    PipelineType.PARTICIPATION: 'participation',
                    PipelineType.MATERIALS_SUPPLY: 'materials',
                    PipelineType.SUBCONTRACTING: 'subcontracting',
                }
                tile_id = tile_map.get(pipeline_type)
                
                # #region agent log
                import json
                log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H3",
                        "location": "main_widget.py:update_stats:update_tile",
                        "message": "Обновление плитки",
                        "data": {
                            "pipeline_type": pipeline_type.value,
                            "tile_id": tile_id,
                            "count": count,
                            "tile_exists": tile_id in self.funnel_tiles if tile_id else False,
                            "funnel_tiles_keys": list(self.funnel_tiles.keys())
                        },
                        "timestamp": int(__import__("time").time() * 1000)
                    }, ensure_ascii=False) + "\n")
                # #endregion
                
                if tile_id and tile_id in self.funnel_tiles:
                    logger.debug(f"Обновляем плитку {tile_id}: count={count}")
                    self.funnel_tiles[tile_id].update_count(count)
                
                # Подсчет по статусам
                for deal in deals:
                    # deal - это объект Deal, не словарь
                    stage_id = deal.stage_id if hasattr(deal, 'stage_id') else None
                    
                    # Упрощенная логика - все сделки считаем "в работе"
                    # TODO: добавить проверку stage_name когда будет доступна
                    in_work_count += 1
            
            # Обновляем карточки статистики
            logger.info(f"Обновляем карточки статистики: stats_cards={len(self.stats_cards)}")
            
            # #region agent log
            import json
            log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H2",
                    "location": "main_widget.py:update_stats:before_update_cards",
                    "message": "Перед обновлением карточек статистики",
                    "data": {
                        "stats_cards_count": len(self.stats_cards),
                        "total_count": total_count,
                        "in_work_count": in_work_count,
                        "won_count": won_count,
                        "new_count": new_count
                    },
                    "timestamp": int(__import__("time").time() * 1000)
                }, ensure_ascii=False) + "\n")
            # #endregion
            
            if len(self.stats_cards) >= 4:
                logger.debug(f"Обновляем карточки: всего={total_count}, в работе={in_work_count}, выиграно={won_count}, новых={new_count}")
                self.stats_cards[0].update_value(total_count)  # Всего
                self.stats_cards[1].update_value(in_work_count)  # В работе
                self.stats_cards[2].update_value(won_count)  # Выиграно
                self.stats_cards[3].update_value(new_count)  # Новых
                
                # #region agent log
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "H4",
                        "location": "main_widget.py:update_stats:after_update_cards",
                        "message": "После вызова update_value для карточек",
                        "data": {"updated": True},
                        "timestamp": int(__import__("time").time() * 1000)
                    }, ensure_ascii=False) + "\n")
                # #endregion
                
                logger.info("Карточки статистики обновлены")
            else:
                logger.warning(f"Недостаточно карточек статистики: {len(self.stats_cards)} < 4")
            
            logger.info(f"=== КОНЕЦ update_stats: всего={total_count}, в работе={in_work_count}, выиграно={won_count}, новых={new_count} ===")
        
        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики воронок: {e}", exc_info=True)
    
    def refresh_funnels(self):
        """Обновление всех воронок"""
        if not self.deal_repo:
            logger.warning("Невозможно обновить воронки: нет подключения к БД")
            return
        
        self.update_stats()
        
        # Обновляем каждую воронку
        if self.participation_widget and hasattr(self.participation_widget, 'load_deals'):
            self.participation_widget.load_deals()
        if self.materials_widget and hasattr(self.materials_widget, 'load_deals'):
            self.materials_widget.load_deals()
        if self.subcontracting_widget and hasattr(self.subcontracting_widget, 'load_deals'):
            self.subcontracting_widget.load_deals()

