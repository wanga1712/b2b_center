from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from loguru import logger

from modules.kp.widget import KPWidget
from modules.bids.widget import BidsWidget
from modules.shipping.widget import ShippingWidget
from modules.clients.widget import ClientsWidget
from modules.tasks.widget import TasksWidget
from modules.ii.artificial_intelligence import AIChatWidget

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
        self.setWindowTitle("🚀 B2B AutoDesk — автоматизация бизнес-процессов")
        
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

        # ----------- Основная область: Боковая панель + Контент -----------
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
        sections = [
            ('КП 🚀', KPWidget(self.db_manager)),  # Коммерческие предложения
            ('Торги 📈', BidsWidget(product_db_manager=self.db_manager)),  # Участие в торгах
            ('Отгрузка 🚚', ShippingWidget()),  # Управление отгрузками
            ('Клиенты 👥', ClientsWidget()),  # Управление клиентами
            ('Задачи ✅', TasksWidget()),  # Управление задачами
            ('AI Ассистент 🤖', AIChatWidget())  # Чат с искусственным интеллектом
        ]

        # Создаем стекированный виджет для переключения между разделами
        self.stacked = QStackedWidget()
        self.stacked.setSizePolicy(QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)  # Растягивается на все доступное пространство

        self.buttons = []  # Список для хранения кнопок навигации

        # Создаем кнопки навигации для каждого раздела
        for i, (name, widget) in enumerate(sections):
            # Создаем кнопку с названием раздела
            btn = QPushButton(name)
            btn.setCheckable(True)  # Кнопка может быть выбрана
            btn.setAutoExclusive(True)  # Только одна кнопка может быть выбрана одновременно

            # При клике на кнопку переключаемся на соответствующий раздел
            btn.clicked.connect(lambda checked, n=i: self.stacked.setCurrentIndex(n))

            # Применяем единый стиль для кнопок сайдбара
            apply_sidebar_button_style(btn)

            side_layout.addWidget(btn)  # Добавляем кнопку в боковую панель
            self.stacked.addWidget(widget)  # Добавляем виджет раздела в стек
            self.buttons.append(btn)  # Сохраняем кнопку в список

        # Выбираем первую кнопку по умолчанию
        self.buttons[0].setChecked(True)
        side_layout.addStretch()  # Растягивающийся элемент для выравнивания кнопок вверху

        # Добавляем боковую панель и область контента в основной layout
        content_layout.addWidget(sidebar)
        content_layout.addWidget(self.stacked)

        main_layout.addLayout(content_layout)
        self.setCentralWidget(central_widget)  # Устанавливаем центральный виджет

        # --------- Единый стиль для области контента -----------
        apply_stacked_style(self.stacked)  # Применяем единый стиль для стекированного виджета

