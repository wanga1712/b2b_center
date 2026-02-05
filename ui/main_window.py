"""
MODULE: ui.main_window
RESPONSIBILITY: Main application window and UI orchestration.
ALLOWED: PyQt5, modules, core.database, config.settings, loguru.
FORBIDDEN: Business logic implementation (should be delegated to widgets/services).
ERRORS: None.
"""
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt, QEvent, QSize, QThread
from PyQt5.QtGui import QCursor, QMoveEvent, QIcon, QPixmap
from pathlib import Path
from loguru import logger

from modules.kp.widget import KPWidget
from modules.bids.widget import BidsWidget
from modules.shipping.widget import ShippingWidget
from modules.clients.widget import ClientsWidget
from modules.tasks.widget import TasksWidget
from modules.ii.artificial_intelligence import AIChatWidget
from modules.crm.home_widget import CRMHomeWidget
from modules.crm.bottom_bar import BottomBar

# Импортируем единые стили
from modules.styles.general_styles import (
    SIZES, get_scaling_info,
    apply_button_style, apply_frame_style, apply_label_style,
    apply_stacked_style, apply_sidebar_button_style, apply_topbar_style
)

# Импортируем менеджер базы данных
from core.database import DatabaseManager
from config.settings import config


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        from modules.styles.ui_config import configure_window
        from PyQt5.QtWidgets import QApplication
        
        configure_window(self, "🚀 B2B AutoDesk — автоматизация бизнес-процессов")
        
        # Настройка размера окна под экран пользователя
        screen = QApplication.primaryScreen()
        size = screen.availableGeometry()
        self.resize(int(size.width() * 1), int(size.height() * 0.97))
        
        # Флаг для отслеживания первого показа окна
        self._first_show = True

        # Инициализация подключения к базе данных
        try:
            self.db_manager = DatabaseManager(config.database)
            self.db_manager.connect()
            logger.info("База данных подключена в главном окне")
        except Exception as e:
            logger.error(f"Ошибка подключения к БД в главном окне: {e}")
            self.db_manager = None

        self.init_ui()

    def showEvent(self, event):
        """Переопределяем showEvent для правильной установки размера и позиции при первом показе"""
        super().showEvent(event)
        
        # Устанавливаем размер и позицию только при первом показе
        if not self._first_show:
            return
        
        self._first_show = False
        
        # Определяем экран, на котором находится или будет находиться окно
        # Сначала пытаемся получить экран, на котором находится окно
        screen = None
        try:
            screen = self.screen()
        except AttributeError:
            # В некоторых версиях PyQt5 метод screen() может быть недоступен
            pass
        
        # Если экран не определен (окно еще не показано), используем экран курсора мыши
        if screen is None:
            # Получаем позицию курсора
            cursor_pos = QCursor.pos()
            # Ищем экран, на котором находится курсор
            screens = QApplication.screens()
            screen = QApplication.primaryScreen()  # По умолчанию главный экран
            
            logger.info(f"Позиция курсора: {cursor_pos.x()}, {cursor_pos.y()}")
            logger.info(f"Найдено экранов: {len(screens)}")
            
            for s in screens:
                screen_geometry = s.geometry()
                device_pixel_ratio = s.devicePixelRatio()
                physical_width = int(screen_geometry.width() * device_pixel_ratio)
                physical_height = int(screen_geometry.height() * device_pixel_ratio)
                
                # Логируем информацию о каждом экране
                logger.info(f"Экран '{s.name()}':")
                logger.info(f"  Геометрия (логическая): {screen_geometry.x()}, {screen_geometry.y()}, {screen_geometry.width()}x{screen_geometry.height()}")
                logger.info(f"  Физическое разрешение: {physical_width}x{physical_height}")
                logger.info(f"  Коэффициент масштабирования: {device_pixel_ratio}")
                logger.info(f"  Курсор в пределах экрана: {screen_geometry.contains(cursor_pos)}")
                
                if screen_geometry.contains(cursor_pos):
                    screen = s
                    logger.info(f"  >>> ВЫБРАН ЭКРАН: {s.name()}")
                    break
        
        if screen is None:
            logger.warning("Не удалось определить экран, используется главный экран")
            screen = QApplication.primaryScreen()
            if screen is None:
                logger.error("Не удалось получить информацию об экране")
                return
        
        # Получаем доступную геометрию экрана (без учета панели задач и системных элементов)
        # availableGeometry уже возвращает правильные логические размеры с учетом масштабирования системы
        available_geometry = screen.availableGeometry()
        
        logger.info(f"Используется экран: {screen.name()}")
        logger.info(f"  Доступная область: {available_geometry.width()}x{available_geometry.height()}")
        logger.info(f"  Позиция доступной области: ({available_geometry.x()}, {available_geometry.y()})")
        
        # Используем 95% от доступной области экрана для безопасного отступа от краев
        window_width = int(available_geometry.width() * 0.95)
        window_height = int(available_geometry.height() * 0.95)
        
        # Вычисляем позицию для центрирования окна в доступной области
        x = available_geometry.x() + (available_geometry.width() - window_width) // 2
        y = available_geometry.y() + (available_geometry.height() - window_height) // 2
        
        # Убеждаемся, что окно не выходит за границы доступной области
        # Проверяем левую и верхнюю границы
        x = max(available_geometry.x(), x)
        y = max(available_geometry.y(), y)
        
        # Проверяем правую и нижнюю границы
        max_x = available_geometry.x() + available_geometry.width() - window_width
        max_y = available_geometry.y() + available_geometry.height() - window_height
        
        if x > max_x:
            x = max_x
        if y > max_y:
            y = max_y
        
        # Финальная проверка: убеждаемся, что окно полностью помещается в доступную область
        if window_width > available_geometry.width():
            window_width = available_geometry.width()
            x = available_geometry.x()
        if window_height > available_geometry.height():
            window_height = available_geometry.height()
            y = available_geometry.y()
        
        # Устанавливаем размер и позицию одновременно
        self.setGeometry(x, y, window_width, window_height)
        
        logger.info(f"Окно установлено на экране '{screen.name()}': позиция ({x}, {y}), размер {window_width}x{window_height} (95% от доступной области {available_geometry.width()}x{available_geometry.height()})")
    
    def moveEvent(self, event: QMoveEvent):
        """Обработка перемещения окна для динамического пересчета масштабирования"""
        super().moveEvent(event)
        # При переносе окна на другой экран пересчитываем масштабирование
        try:
            new_screen = self.screen()
            if new_screen:
                from modules.styles.scaling import GlobalScaling
                scaling = GlobalScaling()
                # Проверяем, изменился ли экран, чтобы не пересчитывать без необходимости
                if not hasattr(self, '_last_screen') or self._last_screen != new_screen:
                    self._last_screen = new_screen
                    scaling.recalculate_for_screen(new_screen)
        except Exception:
            pass  # Молча игнорируем ошибки при пересчете масштабирования

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        # Основной виджет окна
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)  # Убираем промежутки между элементами
        main_layout.setContentsMargins(0, 0, 0, 0)  # Убираем отступы

        # --------- Верхняя панель (TopBar) с едиными стилями ----------
        topbar = QFrame()
        apply_topbar_style(topbar)  # Применяем единый стиль для топбара

        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(30, 8, 40, 8)  # Отступы внутри панели

        # Заголовок приложения
        top_layout.addWidget(QLabel("🚀 B2B AutoDesk — автоматизация бизнес-процессов"))
        top_layout.addStretch()  # Растягивающийся элемент для выравнивания

        # Кнопка создания нового элемента с единым стилем
        btn_new = QPushButton("➕ Создать")
        apply_button_style(btn_new, 'secondary')
        top_layout.addWidget(btn_new)

        # Кнопка экспорта данных с единым стилем
        btn_export = QPushButton("📄 Экспорт")
        apply_button_style(btn_export, 'secondary')
        top_layout.addWidget(btn_export)

        # Кнопка работы с email с единым стилем
        btn_email = QPushButton("✉️ Email")
        apply_button_style(btn_email, 'secondary')
        top_layout.addWidget(btn_email)

        main_layout.addWidget(topbar)

        # ----------- Основная область: Боковая панель + Контент + InfoPanel -----------
        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # ------------- Боковая панель (Sidebar) с едиными стилями --------------
        sidebar = QFrame()
        sidebar.setFixedWidth(SIZES['sidebar_width'])  # Фиксированная ширина боковой панели
        apply_frame_style(sidebar, 'sidebar')  # Применяем единый стиль для сайдбара

        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(20, 40, 18, 20)  # Внутренние отступы

        # Заголовок раздела навигации с единым стилем
        sections_title = QLabel("🗂️ Разделы")
        apply_label_style(sections_title, 'h1')
        side_layout.addWidget(sections_title, alignment=Qt.AlignLeft)
        side_layout.addSpacing(18)  # Отступ после заголовка

        # Список разделов приложения с соответствующими виджетами
        # Передаем db_manager в виджеты, которым это необходимо
        # Создаем виджеты заранее для доступа к ним
        self.kp_widget = KPWidget(self.db_manager)
        self.bids_widget = BidsWidget(product_db_manager=self.db_manager)
        
        # Воронки продаж с Dashboard
        tender_db_manager_for_funnels = None
        if hasattr(self.bids_widget, 'tender_db_manager'):
            tender_db_manager_for_funnels = self.bids_widget.tender_db_manager
            logger.info("tender_db_manager передан в SalesFunnelMainWidget")
        else:
            logger.warning("tender_db_manager не найден в BidsWidget")
        
        from modules.crm.sales_funnel.main_widget import SalesFunnelMainWidget
        self.sales_funnel_widget = SalesFunnelMainWidget(
            tender_db_manager=tender_db_manager_for_funnels,
            user_id=1
        )
        
        self.shipping_widget = ShippingWidget()
        self.clients_widget = ClientsWidget()
        self.tasks_widget = TasksWidget()
        self.ai_widget = AIChatWidget()
        
        # Создаем CRM Home Widget (передаем tender_repo для подменю закупок)
        tender_repo = None
        user_id = 1
        if hasattr(self.bids_widget, 'tender_repo'):
            tender_repo = self.bids_widget.tender_repo
            logger.info(f"tender_repo передан в CRMHomeWidget: {tender_repo is not None}")
        else:
            logger.warning("tender_repo не найден в bids_widget")
        
        if hasattr(self.bids_widget, 'current_user_id'):
            user_id = self.bids_widget.current_user_id
        
        # Передаем search_params_cache из BidsWidget для синхронизации настроек
        search_params_cache = None
        if hasattr(self.bids_widget, 'search_params_cache'):
            search_params_cache = self.bids_widget.search_params_cache
            logger.info("search_params_cache передан из BidsWidget в CRMHomeWidget")
        else:
            logger.warning("search_params_cache не найден в BidsWidget")
        
        self.crm_home_widget = CRMHomeWidget(
            tender_repo=tender_repo,
            user_id=user_id,
            bids_widget=self.bids_widget,
            main_window=self,
            search_params_cache=search_params_cache
        )
        self.crm_home_widget.folder_clicked.connect(self.on_crm_folder_clicked)
        
        # Подключаем обновление счетчиков после загрузки закупок
        # Устанавливаем родителя для BidsWidget, чтобы он мог уведомлять MainWindow
        self.bids_widget.setParent(self)
        
        sections = [
            ('Товары 🚀', self.kp_widget),  # Товары
            ('Закупки 📈', self.bids_widget),  # Управление закупками с Dashboard
            ('Воронки 🎯', self.sales_funnel_widget),  # Воронки продаж с Dashboard
            ('Отгрузка 🚚', self.shipping_widget),  # Управление отгрузками
            ('Клиенты 👥', self.clients_widget),  # Управление клиентами
            ('Задачи ✅', self.tasks_widget),  # Управление задачами
            ('AI Ассистент 🤖', self.ai_widget)  # Чат с искусственным интеллектом
        ]

        # Создаем стекированный виджет для переключения между разделами
        self.stacked = QStackedWidget()
        self.stacked.setSizePolicy(QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)  # Растягивается на все доступное пространство

        self.buttons = []  # Список для хранения кнопок навигации
        self.crm_index = None  # Индекс раздела CRM в стеке

        # Путь к иконке CRM
        crm_icon_path = Path(__file__).parent.parent / 'img' / 'left_menu' / 'crm.png'
        
        # Создаем кнопки навигации для каждого раздела
        for i, (name, widget) in enumerate(sections):
            # Создаем кнопку с названием раздела
            btn = QPushButton(name)
            btn.setCheckable(True)  # Кнопка может быть выбрана
            btn.setAutoExclusive(True)  # Только одна кнопка может быть выбрана одновременно
            
            # Для CRM устанавливаем иконку из файла
            if name == 'CRM 📈' and crm_icon_path.exists():
                icon = QIcon(str(crm_icon_path))
                btn.setIcon(icon)
                # Устанавливаем размер иконки (24x24 пикселей для меню)
                btn.setIconSize(QSize(24, 24))
                # Убираем эмодзи из текста, так как используем иконку
                btn.setText('CRM')

            # При клике на кнопку переключаемся на соответствующий раздел
            btn.clicked.connect(lambda checked, n=i: self.on_section_clicked(n))

            # Применяем единый стиль для кнопок сайдбара
            apply_sidebar_button_style(btn)

            side_layout.addWidget(btn)  # Добавляем кнопку в боковую панель
            self.stacked.addWidget(widget)  # Добавляем виджет раздела в стек
            self.buttons.append(btn)  # Сохраняем кнопку в список
            
            # Сохраняем индекс CRM
            if name == 'CRM 📈':
                self.crm_index = i

        # Выбираем первую кнопку по умолчанию
        self.buttons[0].setChecked(True)
        side_layout.addStretch()  # Растягивающийся элемент для выравнивания кнопок вверху

        # Добавляем боковую панель и область контента в основной layout
        content_layout.addWidget(sidebar)
        content_layout.addWidget(self.stacked)

        main_layout.addLayout(content_layout)
        
        # Создаем виджеты воронок продаж (после создания self.stacked)
        from core.tender_database import TenderDatabaseManager
        from modules.crm.sales_funnel import PipelineRepository, DealRepository, PipelineType
        from modules.crm.sales_funnel.funnel_widget import SalesFunnelWidget
        
        tender_db_manager = None
        if hasattr(self.bids_widget, 'tender_db_manager'):
            tender_db_manager = self.bids_widget.tender_db_manager
        
        if tender_db_manager:
            pipeline_repo = PipelineRepository(tender_db_manager)
            deal_repo = DealRepository(tender_db_manager)
            
            # Получаем tender_repo для синхронизации данных
            tender_repo_for_sync = None
            if hasattr(self.bids_widget, 'tender_repo'):
                tender_repo_for_sync = self.bids_widget.tender_repo
            
            # Получаем user_id для воронок (должен совпадать с user_id при создании сделок)
            funnel_user_id = 1  # По умолчанию
            if hasattr(self.bids_widget, 'current_user_id'):
                funnel_user_id = self.bids_widget.current_user_id
            logger.info(f"Создание виджетов воронок с user_id={funnel_user_id}")
            
            # Создаем виджеты для каждой воронки
            self.sales_funnel_participation = SalesFunnelWidget(
                PipelineType.PARTICIPATION,
                pipeline_repo,
                deal_repo,
                funnel_user_id,
                tender_repo=tender_repo_for_sync
            )
            self.sales_funnel_materials = SalesFunnelWidget(
                PipelineType.MATERIALS_SUPPLY,
                pipeline_repo,
                deal_repo,
                funnel_user_id,
                tender_repo=tender_repo_for_sync
            )
            self.sales_funnel_subcontracting = SalesFunnelWidget(
                PipelineType.SUBCONTRACTING,
                pipeline_repo,
                deal_repo,
                funnel_user_id,
                tender_repo=tender_repo_for_sync
            )
            
            # Добавляем виджеты воронок в стек
            self.stacked.addWidget(self.sales_funnel_participation)
            self.stacked.addWidget(self.sales_funnel_materials)
            self.stacked.addWidget(self.sales_funnel_subcontracting)
        
        # Добавляем BottomBar снизу
        self.bottom_bar = BottomBar()
        main_layout.addWidget(self.bottom_bar)
        
        self.setCentralWidget(central_widget)  # Устанавливаем центральный виджет

        # --------- Единый стиль для области контента -----------
        apply_stacked_style(self.stacked)  # Применяем единый стиль для стекированного виджета
        
        # Фоновое обновление статусов закупок отключено по требованию
        # Ранее: первый запуск через 10 минут после старта, затем каждые 3 часа
    
    # Метод _start_status_updater удален - фоновое обновление статусов отключено по требованию
    
    def on_section_clicked(self, index: int):
        """Обработка клика на раздел в боковом меню"""
        self.stacked.setCurrentIndex(index)
    
    def on_crm_folder_clicked(self, folder_id: str):
        """Обработка клика на папку в CRM Home Widget"""
        logger.info(f"Клик на папку CRM: {folder_id}")
        
        # Маппинг папок на виджеты и вкладки
        folder_to_widget_and_tab = {
            # Закупки (подменю) - разделы по статусам и типам ФЗ
            'purchases_44fz_new': (self.bids_widget, 1),  # Новые закупки 44ФЗ (индекс 1)
            'purchases_44fz_commission': (self.bids_widget, 5),  # Работа комиссии 44 ФЗ (индекс 5)
            'purchases_44fz_won': (self.bids_widget, 3),  # Разыгранные закупки 44ФЗ (индекс 3)
            'purchases_223fz_new': (self.bids_widget, 2),  # Новые закупки 223ФЗ (индекс 2)
            'purchases_223fz_won': (self.bids_widget, 4),  # Разыгранные закупки 223ФЗ (индекс 4)
            # Коммерческие предложения
            'commercial_proposals': (self.kp_widget, None),
            # Клиенты
            'clients_customers': (self.clients_widget, None),
            'clients_contractors': (self.clients_widget, None),
            'clients_designers': (self.clients_widget, None),
            'clients_suppliers': (self.clients_widget, None),
            # Воронки продаж
            'sales_funnel_participation': (getattr(self, 'sales_funnel_participation', None), None),
            'sales_funnel_materials': (getattr(self, 'sales_funnel_materials', None), None),
            'sales_funnel_subcontracting': (getattr(self, 'sales_funnel_subcontracting', None), None),
        }
        
        # Если есть соответствующий виджет, переключаемся на него
        if folder_id in folder_to_widget_and_tab:
            widget, tab_index = folder_to_widget_and_tab[folder_id]
            
            if widget is None:
                logger.warning(f"Виджет для папки {folder_id} не инициализирован")
                return
            
            # Если это BidsWidget, он может быть не в стеке, но мы можем его показать
            if widget == self.bids_widget:
                # Проверяем, есть ли BidsWidget в стеке
                bids_index = None
                for i in range(self.stacked.count()):
                    if self.stacked.widget(i) == self.bids_widget:
                        bids_index = i
                        break
                
                # Если BidsWidget не в стеке, добавляем его
                if bids_index is None:
                    bids_index = self.stacked.count()
                    self.stacked.addWidget(self.bids_widget)
                
                # Переключаемся на BidsWidget
                self.stacked.setCurrentIndex(bids_index)
                
                # НЕ показываем конкретный раздел сразу - показываем Dashboard по умолчанию
                # Пользователь сам выберет раздел из Dashboard плиток
                # Dashboard уже установлен по умолчанию при инициализации BidsWidget
                logger.info(f"BidsWidget открыт, показывается Dashboard (пользователь выберет раздел из плиток)")
                
                # Обновляем кнопку в меню - переключаемся на CRM, так как BidsWidget теперь часть CRM
                if self.crm_index is not None:
                    self.buttons[self.crm_index].setChecked(True)
            elif folder_id.startswith('sales_funnel_'):
                # Для воронок продаж ищем виджет в стеке
                widget_index = None
                for i in range(self.stacked.count()):
                    if self.stacked.widget(i) == widget:
                        widget_index = i
                        break
                
                if widget_index is not None:
                    self.stacked.setCurrentIndex(widget_index)
                    # Обновляем кнопку в меню - переключаемся на CRM
                    if self.crm_index is not None:
                        self.buttons[self.crm_index].setChecked(True)
                else:
                    logger.warning(f"Виджет воронки {folder_id} не найден в стеке")
            else:
                # Для других виджетов ищем в стеке
                for i in range(self.stacked.count()):
                    if self.stacked.widget(i) == widget:
                        self.stacked.setCurrentIndex(i)
                        # Обновляем кнопку в меню
                        self.buttons[i].setChecked(True)
                        break
        else:
            # Для других папок пока просто логируем
            logger.info(f"Папка {folder_id} пока не имеет соответствующего виджета")
    
    def update_purchases_counts(self, category_id=None, user_okpd_codes=None, user_stop_words=None):
        """Обновление счетчиков в подменю закупок после загрузки данных"""
        if hasattr(self, 'crm_home_widget') and self.crm_home_widget:
            # Передаем все фильтры для правильного подсчета
            self.crm_home_widget.counts_update_requested.emit((category_id, user_okpd_codes, user_stop_words))

