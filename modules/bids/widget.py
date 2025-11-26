"""
Виджет для управления закупками (44ФЗ и 223ФЗ)

Виджет предоставляет интерфейс для:
- Управления новыми закупками 44ФЗ и 223ФЗ через канбан-доски
- Просмотра разыгранных закупок
- Настройки параметров закупок
- Отслеживания закупок в работе
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QFrame,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QScrollArea,
    QMessageBox, QComboBox, QDialog, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from typing import Optional, Dict, Any, List
from pathlib import Path
from loguru import logger
import re

# Импортируем единые стили
from modules.styles.general_styles import (
    apply_label_style, apply_frame_style, apply_input_style, apply_button_style,
    COLORS, FONT_SIZES, SIZES, apply_text_style_light_italic
)

# Импортируем виджеты для закупок
from modules.bids.tender_list_widget import TenderListWidget

# Импортируем репозиторий для работы с закупками
from services.tender_repository import TenderRepository
from services.tender_match_repository import TenderMatchRepository
from services.document_search_service import DocumentSearchService
from core.tender_database import TenderDatabaseManager
from config.settings import config
from core.database import DatabaseManager

# DOCUMENT_DOWNLOAD_DIR - путь к директории для скачивания документов из ЕИС
# Настраивается через переменную окружения DOCUMENT_DOWNLOAD_DIR в .env файле
# Пример: DOCUMENT_DOWNLOAD_DIR=C:\Projects\Documents\Tenders


class ProcessOutputReader(QThread):
    """Поток для чтения вывода процесса в реальном времени"""
    
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)
    
    def __init__(self, process):
        super().__init__()
        self.process = process
    
    def run(self):
        """Чтение вывода процесса"""
        try:
            # Для всех платформ используем простой подход с readline
            # stderr объединен с stdout через stderr=subprocess.STDOUT
            while True:
                output = self.process.stdout.readline()
                if not output:
                    # Если строка пустая, проверяем, завершен ли процесс
                    if self.process.poll() is not None:
                        break
                    # Если процесс еще работает, продолжаем ждать
                    continue
                # Отправляем строку (убираем только завершающие символы новой строки)
                self.output_signal.emit(output.rstrip('\n\r'))
            
            # Процесс завершен, читаем оставшийся вывод
            # Используем communicate() только если процесс уже завершен
            try:
                remaining_output, _ = self.process.communicate(timeout=0.1)
                if remaining_output:
                    for line in remaining_output.splitlines():
                        if line.strip():
                            self.output_signal.emit(line.strip())
            except Exception:
                # Игнорируем ошибки при чтении оставшегося вывода
                pass
            
            # Отправляем код завершения
            return_code = self.process.returncode if self.process.returncode is not None else 0
            self.finished_signal.emit(return_code)
        except Exception as e:
            logger.error(f"Ошибка чтения вывода процесса: {e}")
            self.output_signal.emit(f"[ERROR] Ошибка чтения вывода: {e}")
            self.finished_signal.emit(-1)


class ProcessOutputDialog(QDialog):
    """Диалог для отображения вывода консоли процесса"""
    
    def __init__(self, parent=None, title="Вывод процесса"):
        super().__init__(parent)
        from modules.styles.ui_config import configure_dialog
        configure_dialog(self, title, size_preset="xlarge", min_width=800, min_height=600)
        self.setModal(False)  # Не модальное окно, чтобы можно было работать с приложением
        self.process = None
        self.reader_thread = None
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса диалога"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Заголовок
        title_label = QLabel("📊 Вывод процесса обработки документов")
        apply_label_style(title_label, 'h2')
        layout.addWidget(title_label)
        
        # Текстовое поле для вывода
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['white']};
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
                padding: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: {FONT_SIZES['small']};
            }}
        """)
        layout.addWidget(self.output_text)
        
        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_button = QPushButton("Закрыть")
        apply_button_style(self.close_button, 'outline')
        self.close_button.clicked.connect(self.close)
        self.close_button.setEnabled(False)  # Отключаем до завершения процесса
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def start_process(self, process):
        """Запуск процесса и начало чтения вывода"""
        self.process = process
        
        # Создаем и запускаем поток чтения
        self.reader_thread = ProcessOutputReader(process)
        self.reader_thread.output_signal.connect(self.append_output)
        self.reader_thread.finished_signal.connect(self.on_process_finished)
        self.reader_thread.start()
        
        self.append_output("Процесс запущен...")
    
    def append_output(self, text: str):
        """Добавление текста в вывод"""
        if text:
            self.output_text.append(text)
            # Автопрокрутка вниз
            scrollbar = self.output_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def on_process_finished(self, return_code: int):
        """Обработка завершения процесса"""
        if return_code == 0:
            self.append_output("\n[SUCCESS] Процесс успешно завершен.")
        else:
            self.append_output(f"\n[ERROR] Процесс завершен с кодом: {return_code}")
        
        self.close_button.setEnabled(True)
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        if self.reader_thread and self.reader_thread.isRunning():
            # Если процесс еще выполняется, просто закрываем окно
            # Процесс продолжит работу в фоне
            pass
        super().closeEvent(event)


class BidsWidget(QWidget):
    """
    Виджет для управления закупками
    
    Содержит вкладки для различных типов закупок и их статусов.
    """
    
    def __init__(
        self,
        product_db_manager: Optional[DatabaseManager] = None,
        tender_repository: Optional[TenderRepository] = None,
        tender_match_repository: Optional[TenderMatchRepository] = None,
        document_search_service: Optional[DocumentSearchService] = None,
    ):
        """
        Инициализация виджета закупок
        
        Args:
            product_db_manager: Менеджер БД продуктов (для обратной совместимости)
            tender_repository: Репозиторий закупок (опционально, создается через DI если не передан)
            tender_match_repository: Репозиторий результатов поиска (опционально)
            document_search_service: Сервис поиска документов (опционально)
        """
        super().__init__()
        
        # Внедрение зависимостей через DI контейнер или переданные параметры
        from core.dependency_injection import container
        
        # Инициализация подключения к БД tender_monitor (обязательно)
        if not config.tender_database:
            error_msg = "Конфигурация БД tender_monitor не задана. Проверьте переменные окружения в .env файле."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Используем переданные зависимости или создаем через контейнер
            if tender_repository:
                self.tender_repo = tender_repository
                self.tender_db_manager = tender_repository.db_manager if hasattr(tender_repository, 'db_manager') else None
            else:
                self.tender_db_manager = container.get_tender_database_manager()
                self.tender_repo = container.get_tender_repository()
            
            if tender_match_repository:
                self.tender_match_repo = tender_match_repository
            else:
                self.tender_match_repo = container.get_tender_match_repository()
            # Алиас для обратной совместимости с новым именем атрибута
            self.tender_match_repository = self.tender_match_repo
            
            logger.info("Подключение к БД tender_monitor установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к БД tender_monitor: {e}")
            raise  # Пробрасываем ошибку, так как подключение обязательно
        
        # Временный ID пользователя (позже будет из системы авторизации)
        self.current_user_id = 1
        self.product_db_manager = product_db_manager
        
        # Инициализация сервиса поиска документов
        if document_search_service:
            self.document_search_service = document_search_service
        elif self.product_db_manager:
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
            # Пытаемся получить через контейнер
            try:
                self.document_search_service = container.get_document_search_service()
                logger.info("Сервис поиска по документации получен через DI контейнер")
            except Exception as e:
                logger.warning(f"Сервис поиска документации недоступен: {e}")
                self.document_search_service = None
        
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
        
        # Заголовок и кнопка обновления в одной строке
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("📈 Закупки")
        apply_label_style(title, 'h1')
        header_row.addWidget(title)
        
        header_row.addStretch()
        
        # Кнопка анализа документации для выбранных закупок
        self.analyze_button = QPushButton("📄 Анализ выбранных")
        apply_button_style(self.analyze_button, 'primary')
        self.analyze_button.clicked.connect(self.handle_analyze_selected_tenders)
        self.analyze_button.setToolTip("Запустить анализ документации для выбранных закупок")
        self.analyze_button.setEnabled(False)  # Включается только когда есть выбранные закупки
        header_row.addWidget(self.analyze_button)
        
        # Кнопка анализа всех закупок (с учетом приоритетных)
        self.analyze_all_button = QPushButton("📊 Анализировать все")
        apply_button_style(self.analyze_all_button, 'secondary')
        self.analyze_all_button.clicked.connect(self.handle_analyze_all_tenders)
        self.analyze_all_button.setToolTip("Запустить анализ документации для всех закупок (приоритетные обрабатываются первыми)")
        header_row.addWidget(self.analyze_all_button)
        
        # Кнопка обновления ленты
        self.refresh_button = QPushButton("🔄 Обновить ленту")
        apply_button_style(self.refresh_button, 'outline')
        self.refresh_button.clicked.connect(self.refresh_current_feed)
        self.refresh_button.setToolTip("Обновить статусы обработки документов для всех закупок")
        header_row.addWidget(self.refresh_button)
        
        header_layout.addLayout(header_row)
        
        main_layout.addWidget(header_frame)
        
        # Вкладки для различных разделов закупок
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
        
        # === ВКЛАДКА "НОВЫЕ ЗАКУПКИ 44ФЗ" ===
        self.tenders_44fz_widget = TenderListWidget(
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repo,
        )
        self.tabs.addTab(self.tenders_44fz_widget, "Новые закупки 44ФЗ")
        # Загружаем закупки при первом показе вкладки
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # === ВКЛАДКА "НОВЫЕ ЗАКУПКИ 223ФЗ" ===
        self.tenders_223fz_widget = TenderListWidget(
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repo,
        )
        self.tabs.addTab(self.tenders_223fz_widget, "Новые закупки 223ФЗ")
        
        # === ВКЛАДКА "РАЗЫГРАННЫЕ ЗАКУПКИ 44ФЗ" ===
        self.won_tenders_44fz_widget = TenderListWidget(
            parent=self,
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repository,
        )
        self.tabs.addTab(self.won_tenders_44fz_widget, "Разыгранные закупки 44ФЗ")
        
        # === ВКЛАДКА "РАЗЫГРАННЫЕ ЗАКУПКИ 223ФЗ" ===
        self.won_tenders_223fz_widget = TenderListWidget(
            parent=self,
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repository,
        )
        self.tabs.addTab(self.won_tenders_223fz_widget, "Разыгранные закупки 223ФЗ")
        
        # === ВКЛАДКА "В РАБОТЕ" ===
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
        
        self.tabs.addTab(in_work_tab, "В работе")
        
        # Добавляем вкладки в основной layout
        main_layout.addWidget(self.tabs)
    
    def on_tab_changed(self, index: int):
        """Обработка смены вкладки - НЕ загружаем данные автоматически"""
        # Загрузка данных теперь происходит только по кнопке "Показать тендеры"
        pass
    
    def refresh_current_feed(self):
        """Обновление текущей ленты закупок"""
        current_index = self.tabs.currentIndex()
        tab_text = self.tabs.tabText(current_index)
        
        if tab_text == "Новые закупки 44ФЗ":
            logger.info("Обновление ленты закупок 44ФЗ...")
            self.load_tenders_44fz(force=True)
            self.tenders_44fz_widget._loaded = True
        elif tab_text == "Новые закупки 223ФЗ":
            logger.info("Обновление ленты закупок 223ФЗ...")
            self.load_tenders_223fz(force=True)
            self.tenders_223fz_widget._loaded = True
        elif tab_text == "Разыгранные закупки 44ФЗ":
            logger.info("Обновление ленты разыгранных закупок 44ФЗ...")
            self.load_won_tenders_44fz(force=True)
            self.won_tenders_44fz_widget._loaded = True
        elif tab_text == "Разыгранные закупки 223ФЗ":
            logger.info("Обновление ленты разыгранных закупок 223ФЗ...")
            self.load_won_tenders_223fz(force=True)
            self.won_tenders_223fz_widget._loaded = True
        else:
            logger.info(f"Обновление недоступно для вкладки: {tab_text}")
    
    def load_tenders_44fz(self, force: bool = False):
        """Загрузка новых закупок 44ФЗ"""
        if not self.tender_repo:
            logger.warning("Репозиторий закупок не инициализирован")
            return
        
        # Показываем индикатор загрузки
        self.tenders_44fz_widget.show_loading()
        
        # Получаем настройки пользователя
        # Проверяем, выбрана ли категория для фильтрации
        category_id = None
        if hasattr(self, 'category_filter_combo') and self.category_filter_combo:
            category_id = self.category_filter_combo.currentData()
        
        user_okpd_codes = None
        if category_id is None:
            # Если категория не выбрана, используем все ОКПД коды пользователя
            user_okpd = self.tender_repo.get_user_okpd_codes(self.current_user_id)
            user_okpd_codes = [okpd.get('okpd_code', '') for okpd in user_okpd if okpd.get('okpd_code')]
        
        user_stop_words_data = self.tender_repo.get_user_stop_words(self.current_user_id)
        user_stop_words = [sw.get('stop_word', '') for sw in user_stop_words_data if sw.get('stop_word')]
        
        # TODO: Получить region_id из настроек пользователя (пока None = все регионы)
        region_id = None
        
        # Загружаем закупки в отдельном потоке (упрощенная версия - можно улучшить)
        try:
            tenders = self.tender_repo.get_new_tenders_44fz(
                user_id=self.current_user_id,
                user_okpd_codes=user_okpd_codes,
                user_stop_words=user_stop_words,
                region_id=region_id,
                category_id=category_id,
                limit=1000  # Увеличено до 1000 закупок для отображения
            )
            # Извлекаем информацию о количестве из первого элемента
            total_count = None
            if tenders and '_total_count' in tenders[0]:
                total_count = tenders[0].pop('_total_count', len(tenders))
                tenders[0].pop('_loaded_count', None)  # Удаляем служебное поле
            
            logger.info(f"Отображаем закупки 44ФЗ: {len(tenders)} (всего в БД: {total_count})")
            
            if force:
                # Принудительное обновление - пересоздаем карточки
                self.tenders_44fz_widget.set_tenders(tenders, total_count)
            else:
                # Обычная загрузка - обновляем существующие карточки или создаем новые
                self.tenders_44fz_widget.update_tenders(tenders, total_count)
            
            if self.document_search_service:
                self.document_search_service.ensure_products_loaded()
        except Exception as e:
            logger.error(f"Ошибка при загрузке закупок 44ФЗ: {e}")
            self.tenders_44fz_widget.hide_loading()
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить закупки:\n{e}")
    
    def load_tenders_223fz(self, force: bool = False):
        """Загрузка новых закупок 223ФЗ"""
        if not self.tender_repo:
            logger.warning("Репозиторий закупок не инициализирован")
            return
        
        # Показываем индикатор загрузки
        self.tenders_223fz_widget.show_loading()
        
        # Получаем настройки пользователя
        # Проверяем, выбрана ли категория для фильтрации
        category_id = None
        if hasattr(self, 'category_filter_combo') and self.category_filter_combo:
            category_id = self.category_filter_combo.currentData()
        
        user_okpd_codes = None
        if category_id is None:
            # Если категория не выбрана, используем все ОКПД коды пользователя
            user_okpd = self.tender_repo.get_user_okpd_codes(self.current_user_id)
            user_okpd_codes = [okpd.get('okpd_code', '') for okpd in user_okpd if okpd.get('okpd_code')]
        
        user_stop_words_data = self.tender_repo.get_user_stop_words(self.current_user_id)
        user_stop_words = [sw.get('stop_word', '') for sw in user_stop_words_data if sw.get('stop_word')]
        
        # TODO: Получить region_id из настроек пользователя (пока None = все регионы)
        region_id = None
        
        # Загружаем закупки
        try:
            tenders = self.tender_repo.get_new_tenders_223fz(
                user_id=self.current_user_id,
                user_okpd_codes=user_okpd_codes,
                user_stop_words=user_stop_words,
                region_id=region_id,
                category_id=category_id,
                limit=1000  # Увеличено до 1000 закупок для отображения
            )
            # Извлекаем информацию о количестве из первого элемента
            total_count = None
            if tenders and '_total_count' in tenders[0]:
                total_count = tenders[0].pop('_total_count', len(tenders))
                tenders[0].pop('_loaded_count', None)  # Удаляем служебное поле
            
            logger.info(f"Отображаем закупки 223ФЗ: {len(tenders)} (всего в БД: {total_count})")
            
            if force:
                # Принудительное обновление - пересоздаем карточки
                self.tenders_223fz_widget.set_tenders(tenders, total_count)
            else:
                # Обычная загрузка - обновляем существующие карточки или создаем новые
                self.tenders_223fz_widget.update_tenders(tenders, total_count)
            
            if self.document_search_service:
                self.document_search_service.ensure_products_loaded()
        except Exception as e:
            logger.error(f"Ошибка при загрузке закупок 223ФЗ: {e}")
            self.tenders_223fz_widget.hide_loading()
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить закупки:\n{e}")
    
    def load_won_tenders_44fz(self, force: bool = False):
        """Загрузка разыгранных закупок 44ФЗ"""
        if not self.tender_repo:
            logger.warning("Репозиторий закупок не инициализирован")
            return
        
        # Показываем индикатор загрузки
        self.won_tenders_44fz_widget.show_loading()
        
        # Получаем настройки пользователя
        category_id = None
        if hasattr(self, 'category_filter_combo') and self.category_filter_combo:
            category_id = self.category_filter_combo.currentData()
        
        user_okpd_codes = None
        if category_id is None:
            user_okpd = self.tender_repo.get_user_okpd_codes(self.current_user_id)
            user_okpd_codes = [okpd.get('okpd_code', '') for okpd in user_okpd if okpd.get('okpd_code')]
        
        user_stop_words_data = self.tender_repo.get_user_stop_words(self.current_user_id)
        user_stop_words = [sw.get('stop_word', '') for sw in user_stop_words_data if sw.get('stop_word')]
        
        region_id = None
        
        try:
            tenders = self.tender_repo.get_won_tenders_44fz(
                user_id=self.current_user_id,
                user_okpd_codes=user_okpd_codes,
                user_stop_words=user_stop_words,
                region_id=region_id,
                category_id=category_id,
                limit=1000
            )
            total_count = None
            if tenders and '_total_count' in tenders[0]:
                total_count = tenders[0].pop('_total_count', len(tenders))
                tenders[0].pop('_loaded_count', None)
            
            logger.info(f"Отображаем разыгранные закупки 44ФЗ: {len(tenders)} (всего в БД: {total_count})")
            
            if force:
                self.won_tenders_44fz_widget.set_tenders(tenders, total_count)
            else:
                self.won_tenders_44fz_widget.update_tenders(tenders, total_count)
            
            if self.document_search_service:
                self.document_search_service.ensure_products_loaded()
        except Exception as e:
            logger.error(f"Ошибка при загрузке разыгранных закупок 44ФЗ: {e}")
            self.won_tenders_44fz_widget.hide_loading()
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить закупки:\n{e}")
    
    def load_won_tenders_223fz(self, force: bool = False):
        """Загрузка разыгранных закупок 223ФЗ"""
        if not self.tender_repo:
            logger.warning("Репозиторий закупок не инициализирован")
            return
        
        # Показываем индикатор загрузки
        self.won_tenders_223fz_widget.show_loading()
        
        # Получаем настройки пользователя
        category_id = None
        if hasattr(self, 'category_filter_combo') and self.category_filter_combo:
            category_id = self.category_filter_combo.currentData()
        
        user_okpd_codes = None
        if category_id is None:
            user_okpd = self.tender_repo.get_user_okpd_codes(self.current_user_id)
            user_okpd_codes = [okpd.get('okpd_code', '') for okpd in user_okpd if okpd.get('okpd_code')]
        
        user_stop_words_data = self.tender_repo.get_user_stop_words(self.current_user_id)
        user_stop_words = [sw.get('stop_word', '') for sw in user_stop_words_data if sw.get('stop_word')]
        
        region_id = None
        
        try:
            tenders = self.tender_repo.get_won_tenders_223fz(
                user_id=self.current_user_id,
                user_okpd_codes=user_okpd_codes,
                user_stop_words=user_stop_words,
                region_id=region_id,
                category_id=category_id,
                limit=1000
            )
            total_count = None
            if tenders and '_total_count' in tenders[0]:
                total_count = tenders[0].pop('_total_count', len(tenders))
                tenders[0].pop('_loaded_count', None)
            
            logger.info(f"Отображаем разыгранные закупки 223ФЗ: {len(tenders)} (всего в БД: {total_count})")
            
            if force:
                self.won_tenders_223fz_widget.set_tenders(tenders, total_count)
            else:
                self.won_tenders_223fz_widget.update_tenders(tenders, total_count)
            
            if self.document_search_service:
                self.document_search_service.ensure_products_loaded()
        except Exception as e:
            logger.error(f"Ошибка при загрузке разыгранных закупок 223ФЗ: {e}")
            self.won_tenders_223fz_widget.hide_loading()
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить закупки:\n{e}")
    
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
        settings_label = QLabel("Настройки закупок")
        apply_label_style(settings_label, 'h2')
        settings_layout.addWidget(settings_label)
        
        # === РАЗДЕЛ ВЫБОРА КАТЕГОРИИ ДЛЯ ФИЛЬТРАЦИИ ЗАКУПОК ===
        filter_category_frame = QFrame()
        apply_frame_style(filter_category_frame, 'content')
        filter_category_layout = QVBoxLayout(filter_category_frame)
        filter_category_layout.setContentsMargins(15, 15, 15, 15)
        filter_category_layout.setSpacing(10)
        
        filter_category_title = QLabel("Фильтрация закупок по категории")
        apply_label_style(filter_category_title, 'h3')
        filter_category_layout.addWidget(filter_category_title)
        
        filter_category_info = QLabel("Выберите категорию ОКПД для фильтрации закупок. Будут показаны только закупки с ОКПД кодами из выбранной категории.")
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
        
        settings_layout.addWidget(filter_category_frame)
        
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
        
        # === РАЗДЕЛ УПРАВЛЕНИЯ КАТЕГОРИЯМИ ОКПД ===
        categories_frame = QFrame()
        apply_frame_style(categories_frame, 'content')
        categories_layout = QVBoxLayout(categories_frame)
        categories_layout.setContentsMargins(15, 15, 15, 15)
        categories_layout.setSpacing(10)
        
        categories_title = QLabel("Категории ОКПД")
        apply_label_style(categories_title, 'h3')
        categories_layout.addWidget(categories_title)
        
        categories_info = QLabel("Создавайте категории для группировки ОКПД кодов (например: компьютеры, стройка, проекты). При выборе категории в поиске закупок будут отображаться только закупки с ОКПД кодами из этой категории.")
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
        self.categories_list.setStyleSheet(f"""
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
        
        settings_layout.addWidget(categories_frame)
        
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
        
        stop_words_info = QLabel("Стоп-слова используются для фильтрации закупок. Закупки, содержащие стоп-слова, будут исключены из результатов.")
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
        
        # === КНОПКА ПОКАЗАТЬ ТЕНДЕРЫ ===
        show_tenders_frame = QFrame()
        apply_frame_style(show_tenders_frame, 'content')
        show_tenders_layout = QVBoxLayout(show_tenders_frame)
        show_tenders_layout.setContentsMargins(15, 15, 15, 15)
        show_tenders_layout.setSpacing(10)
        
        show_tenders_info = QLabel("После настройки фильтров нажмите кнопку ниже, чтобы загрузить закупки по выбранным критериям.")
        apply_label_style(show_tenders_info, 'small')
        apply_text_style_light_italic(show_tenders_info)
        show_tenders_info.setWordWrap(True)
        show_tenders_layout.addWidget(show_tenders_info)
        
        btn_show_tenders = QPushButton("🔍 Показать тендеры")
        apply_button_style(btn_show_tenders, 'primary')
        btn_show_tenders.clicked.connect(self.handle_show_tenders)
        btn_show_tenders.setMinimumHeight(50)
        show_tenders_layout.addWidget(btn_show_tenders)
        
        settings_layout.addWidget(show_tenders_frame)
        
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
        
        # Загружаем категории ОКПД
        self.load_okpd_categories()
        
        # Загружаем добавленные ОКПД пользователя
        self.load_user_okpd_codes()
        
        # Загружаем стоп-слова пользователя
        self.load_user_stop_words()
        
        return settings_tab
    
    def load_okpd_codes(self, search_text: Optional[str] = None):
        """Загрузка списка ОКПД кодов с учетом выбранного региона"""
        if not self.tender_repo:
            logger.warning("Репозиторий закупок не инициализирован, ОКПД не загружены")
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
        """Обработка добавления выбранного ОКПД с возможностью выбора категории"""
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
        
        # Запрашиваем категорию (опционально)
        category_id = None
        categories = self.tender_repo.get_okpd_categories(self.current_user_id)
        if categories:
            from PyQt5.QtWidgets import QInputDialog
            category_names = [cat.get('name', 'Без названия') for cat in categories]
            category_names.insert(0, "Без категории")
            
            selected, ok = QInputDialog.getItem(
                self,
                "Выбор категории",
                f"Выберите категорию для ОКПД кода {okpd_code}:",
                category_names,
                0,
                False
            )
            
            if ok and selected != "Без категории":
                # Находим ID выбранной категории
                for cat in categories:
                    if cat.get('name') == selected:
                        category_id = cat.get('id')
                        break
        
        # Проверяем, существует ли уже этот код (для правильного сообщения)
        from psycopg2.extras import RealDictCursor
        
        check_query = """
            SELECT id, category_id FROM okpd_from_users 
            WHERE user_id = %s AND okpd_code = %s
        """
        existing_check = self.tender_repo.db_manager.execute_query(
            check_query,
            (self.current_user_id, okpd_code),
            RealDictCursor
        )
        
        was_existing = bool(existing_check)
        existing_category_id = existing_check[0].get('category_id') if existing_check else None
        
        # Добавляем код (или получаем существующий ID)
        okpd_id = self.tender_repo.add_user_okpd_code(
            user_id=self.current_user_id,
            okpd_code=okpd_code,
            name=okpd_data.get('name')
        )
        
        if not okpd_id:
            QMessageBox.warning(self, "Ошибка", "Не удалось добавить код ОКПД")
            return
        
        # Если выбрана категория, всегда привязываем/обновляем категорию
        if category_id:
            success = self.tender_repo.assign_okpd_to_category(
                user_id=self.current_user_id,
                okpd_id=okpd_id,
                category_id=category_id
            )
            if success:
                if was_existing:
                    if existing_category_id == category_id:
                        QMessageBox.information(
                            self, 
                            "Информация", 
                            f"Код ОКПД {okpd_code} уже был добавлен с этой категорией."
                        )
                    else:
                        QMessageBox.information(
                            self, 
                            "Успех", 
                            f"Код ОКПД {okpd_code} уже был добавлен. Категория обновлена."
                        )
                else:
                    QMessageBox.information(self, "Успех", f"Код ОКПД {okpd_code} добавлен и привязан к категории")
            else:
                QMessageBox.warning(
                    self, 
                    "Предупреждение", 
                    f"Код ОКПД {okpd_code} {'добавлен' if not was_existing else 'уже был добавлен'}, но не удалось {'установить' if not was_existing else 'обновить'} категорию."
                )
        else:
            # Категория не выбрана
            if was_existing:
                QMessageBox.information(
                    self, 
                    "Информация", 
                    f"Код ОКПД {okpd_code} уже был добавлен ранее."
                )
            else:
                QMessageBox.information(self, "Успех", f"Код ОКПД {okpd_code} добавлен")
        
        # Обновляем список добавленных ОКПД
        self.load_user_okpd_codes()
    
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
            logger.warning("Репозиторий закупок не инициализирован, регионы не загружены")
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
    
    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С КАТЕГОРИЯМИ ОКПД ==========
    
    def load_okpd_categories(self):
        """Загрузка и отображение категорий ОКПД пользователя"""
        if not self.tender_repo:
            return
        
        try:
            categories = self.tender_repo.get_okpd_categories(self.current_user_id)
            
            # Загружаем в список категорий
            if hasattr(self, 'categories_list'):
                self.categories_list.clear()
                for category in categories:
                    category_name = category.get('name', 'Без названия')
                    category_id = category.get('id')
                    item_text = f"{category_name}"
                    if category.get('description'):
                        item_text += f" - {category.get('description')[:50]}"
                    
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, category)
                    self.categories_list.addItem(item)
            
            # Загружаем в комбобокс фильтра
            if hasattr(self, 'category_filter_combo'):
                current_data = self.category_filter_combo.currentData()
                self.category_filter_combo.clear()
                self.category_filter_combo.addItem("Все категории", None)
                for category in categories:
                    category_name = category.get('name', 'Без названия')
                    category_id = category.get('id')
                    self.category_filter_combo.addItem(category_name, category_id)
                
                # Восстанавливаем выбранную категорию
                if current_data is not None:
                    for i in range(self.category_filter_combo.count()):
                        if self.category_filter_combo.itemData(i) == current_data:
                            self.category_filter_combo.setCurrentIndex(i)
                            break
        except Exception as e:
            logger.error(f"Ошибка при загрузке категорий ОКПД: {e}")
    
    def on_category_filter_changed(self, index: int):
        """Обработка изменения выбранной категории для фильтрации"""
        # Автоматически обновляем закупки при изменении категории
        if hasattr(self, 'tabs') and self.tabs:
            current_index = self.tabs.currentIndex()
            if current_index == 0:  # Вкладка "Новые закупки 44ФЗ"
                self.load_tenders_44fz(force=True)
            elif current_index == 1:  # Вкладка "Новые закупки 223ФЗ"
                self.load_tenders_223fz(force=True)
            elif current_index == 2 and hasattr(self, 'won_tenders_44fz_widget'):
                self.load_won_tenders_44fz(force=True)
            elif current_index == 3 and hasattr(self, 'won_tenders_223fz_widget'):
                self.load_won_tenders_223fz(force=True)
    
    def handle_create_category(self):
        """Обработка создания новой категории ОКПД"""
        if not self.tender_repo:
            QMessageBox.warning(self, "Ошибка", "Нет подключения к базе данных")
            return
        
        category_name = self.category_name_input.text().strip()
        if not category_name:
            QMessageBox.warning(self, "Предупреждение", "Введите название категории")
            return
        
        category_id = self.tender_repo.create_okpd_category(
            user_id=self.current_user_id,
            name=category_name
        )
        
        if category_id:
            QMessageBox.information(self, "Успех", f"Категория '{category_name}' создана")
            self.category_name_input.clear()
            self.load_okpd_categories()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось создать категорию")
    
    def handle_delete_category(self):
        """Обработка удаления категории ОКПД"""
        if not self.tender_repo:
            QMessageBox.warning(self, "Ошибка", "Нет подключения к базе данных")
            return
        
        current_item = self.categories_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Предупреждение", "Выберите категорию для удаления")
            return
        
        category_data = current_item.data(Qt.UserRole)
        if not category_data:
            return
        
        category_id = category_data.get('id')
        category_name = category_data.get('name', 'категория')
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить категорию '{category_name}'?\n\nОКПД коды из этой категории останутся, но будут отвязаны от категории.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.tender_repo.delete_okpd_category(category_id, self.current_user_id)
            if success:
                QMessageBox.information(self, "Успех", f"Категория '{category_name}' удалена")
                self.load_okpd_categories()
                self.load_user_okpd_codes()  # Обновляем список ОКПД, чтобы показать изменения
    
    def handle_show_tenders(self):
        """Обработка нажатия кнопки 'Показать тендеры'"""
        # Переключаемся на первую вкладку с закупками
        self.tabs.setCurrentIndex(0)  # Вкладка "Новые закупки 44ФЗ"
        # Загружаем закупки 44ФЗ
        self.load_tenders_44fz(force=True)
        # Переключаемся на вторую вкладку и загружаем 223ФЗ
        self.tabs.setCurrentIndex(1)  # Вкладка "Новые закупки 223ФЗ"
        self.load_tenders_223fz(force=True)
        # Загружаем разыгранные закупки 44ФЗ
        if hasattr(self, 'won_tenders_44fz_widget'):
            self.tabs.setCurrentIndex(2)
            self.load_won_tenders_44fz(force=True)
        # Загружаем разыгранные закупки 223ФЗ
        if hasattr(self, 'won_tenders_223fz_widget'):
            self.tabs.setCurrentIndex(3)
            self.load_won_tenders_223fz(force=True)
        # Возвращаемся на первую вкладку
        self.tabs.setCurrentIndex(0)
        QMessageBox.information(self, "Успех", "Закупки загружены по выбранным критериям")
    
    def on_tender_selection_changed(self):
        """Обработка изменения выбора закупок"""
        # Подсчитываем выбранные закупки из всех виджетов
        selected_44fz = self.tenders_44fz_widget.get_selected_tenders() if hasattr(self.tenders_44fz_widget, 'get_selected_tenders') else []
        selected_223fz = self.tenders_223fz_widget.get_selected_tenders() if hasattr(self.tenders_223fz_widget, 'get_selected_tenders') else []
        
        # Добавляем выбранные из разыгранных контрактов
        if hasattr(self, 'won_tenders_44fz_widget'):
            selected_44fz.extend(self.won_tenders_44fz_widget.get_selected_tenders() if hasattr(self.won_tenders_44fz_widget, 'get_selected_tenders') else [])
        if hasattr(self, 'won_tenders_223fz_widget'):
            selected_223fz.extend(self.won_tenders_223fz_widget.get_selected_tenders() if hasattr(self.won_tenders_223fz_widget, 'get_selected_tenders') else [])
        
        total_selected = len(selected_44fz) + len(selected_223fz)
        
        # Включаем/выключаем кнопку анализа
        if hasattr(self, 'analyze_button'):
            self.analyze_button.setEnabled(total_selected > 0)
            if total_selected > 0:
                self.analyze_button.setText(f"📄 Анализ выбранных ({total_selected})")
            else:
                self.analyze_button.setText("📄 Анализ выбранных")
    
    def handle_analyze_selected_tenders(self):
        """Обработка нажатия кнопки 'Анализ документации'"""
        # Определяем текущую вкладку
        current_index = self.tabs.currentIndex()
        tab_text = self.tabs.tabText(current_index)
        
        # Получаем выбранные закупки из текущей вкладки
        selected_44fz = []
        selected_223fz = []
        
        if tab_text == "Новые закупки 44ФЗ":
            selected_44fz = self.tenders_44fz_widget.get_selected_tenders() if hasattr(self.tenders_44fz_widget, 'get_selected_tenders') else []
        elif tab_text == "Новые закупки 223ФЗ":
            selected_223fz = self.tenders_223fz_widget.get_selected_tenders() if hasattr(self.tenders_223fz_widget, 'get_selected_tenders') else []
        elif tab_text == "Разыгранные закупки 44ФЗ":
            selected_44fz = self.won_tenders_44fz_widget.get_selected_tenders() if hasattr(self.won_tenders_44fz_widget, 'get_selected_tenders') else []
        elif tab_text == "Разыгранные закупки 223ФЗ":
            selected_223fz = self.won_tenders_223fz_widget.get_selected_tenders() if hasattr(self.won_tenders_223fz_widget, 'get_selected_tenders') else []
        else:
            # Для других вкладок получаем из всех виджетов
            selected_44fz = self.tenders_44fz_widget.get_selected_tenders() if hasattr(self.tenders_44fz_widget, 'get_selected_tenders') else []
            selected_223fz = self.tenders_223fz_widget.get_selected_tenders() if hasattr(self.tenders_223fz_widget, 'get_selected_tenders') else []
            if hasattr(self, 'won_tenders_44fz_widget'):
                selected_44fz.extend(self.won_tenders_44fz_widget.get_selected_tenders() if hasattr(self.won_tenders_44fz_widget, 'get_selected_tenders') else [])
            if hasattr(self, 'won_tenders_223fz_widget'):
                selected_223fz.extend(self.won_tenders_223fz_widget.get_selected_tenders() if hasattr(self.won_tenders_223fz_widget, 'get_selected_tenders') else [])
        
        if not selected_44fz and not selected_223fz:
            QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы одну закупку для анализа")
            return
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Запустить анализ документации для {len(selected_44fz) + len(selected_223fz)} выбранных закупок?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Запускаем обработку документов для выбранных закупок
            self._run_document_processing_for_selected(selected_44fz, selected_223fz)
    
    def handle_analyze_all_tenders(self):
        """Обработка нажатия кнопки 'Анализировать все'"""
        # Определяем текущую вкладку
        current_index = self.tabs.currentIndex()
        tab_text = self.tabs.tabText(current_index)
        
        # Получаем приоритетные (выбранные) закупки только из текущей вкладки
        priority_44fz = []
        priority_223fz = []
        
        if tab_text == "Новые закупки 44ФЗ":
            priority_44fz = self.tenders_44fz_widget.get_selected_tenders() if hasattr(self.tenders_44fz_widget, 'get_selected_tenders') else []
            registry_type = '44fz'
        elif tab_text == "Новые закупки 223ФЗ":
            priority_223fz = self.tenders_223fz_widget.get_selected_tenders() if hasattr(self.tenders_223fz_widget, 'get_selected_tenders') else []
            registry_type = '223fz'
        elif tab_text == "Разыгранные закупки 44ФЗ":
            priority_44fz = self.won_tenders_44fz_widget.get_selected_tenders() if hasattr(self.won_tenders_44fz_widget, 'get_selected_tenders') else []
            registry_type = '44fz'
        elif tab_text == "Разыгранные закупки 223ФЗ":
            priority_223fz = self.won_tenders_223fz_widget.get_selected_tenders() if hasattr(self.won_tenders_223fz_widget, 'get_selected_tenders') else []
            registry_type = '223fz'
        else:
            # Для других вкладок используем обе
            priority_44fz = self.tenders_44fz_widget.get_selected_tenders() if hasattr(self.tenders_44fz_widget, 'get_selected_tenders') else []
            priority_223fz = self.tenders_223fz_widget.get_selected_tenders() if hasattr(self.tenders_223fz_widget, 'get_selected_tenders') else []
            if hasattr(self, 'won_tenders_44fz_widget'):
                priority_44fz.extend(self.won_tenders_44fz_widget.get_selected_tenders() if hasattr(self.won_tenders_44fz_widget, 'get_selected_tenders') else [])
            if hasattr(self, 'won_tenders_223fz_widget'):
                priority_223fz.extend(self.won_tenders_223fz_widget.get_selected_tenders() if hasattr(self.won_tenders_223fz_widget, 'get_selected_tenders') else [])
            registry_type = None
        
        priority_count = len(priority_44fz) + len(priority_223fz)
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Запустить анализ документации для всех закупок{' ' + tab_text if registry_type else ''}?\n\n"
            f"Приоритетных (выбранных): {priority_count}\n"
            f"Приоритетные закупки будут обработаны первыми.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Запускаем обработку всех закупок с учетом приоритетных и типа реестра
            self._run_document_processing_for_all(priority_44fz, priority_223fz, registry_type=registry_type)
    
    def _run_document_processing_for_selected(self, selected_44fz: List[Dict[str, Any]], selected_223fz: List[Dict[str, Any]]):
        """Запуск обработки документов для выбранных закупок"""
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            # Формируем список ID выбранных закупок
            tender_ids_44fz = [t.get('id') for t in selected_44fz if t.get('id')]
            tender_ids_223fz = [t.get('id') for t in selected_223fz if t.get('id')]
            
            if not tender_ids_44fz and not tender_ids_223fz:
                QMessageBox.warning(self, "Ошибка", "Не удалось определить ID выбранных закупок")
                return
            
            # Формируем строку аргументов для скрипта
            tenders_arg_parts = []
            if tender_ids_44fz:
                ids_str = ','.join(map(str, tender_ids_44fz))
                tenders_arg_parts.append(f"44fz:{ids_str}")
            if tender_ids_223fz:
                ids_str = ','.join(map(str, tender_ids_223fz))
                tenders_arg_parts.append(f"223fz:{ids_str}")
            
            tenders_arg = ' '.join(tenders_arg_parts)
            
            # Запускаем скрипт обработки документов
            script_path = Path(__file__).parent.parent.parent / "scripts" / "run_document_processing.py"
            
            if not script_path.exists():
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Скрипт обработки документов не найден:\n{script_path}"
                )
                return
            
            # Запускаем скрипт с аргументами
            cmd = [sys.executable, str(script_path), '--tenders', tenders_arg, '--user-id', str(self.current_user_id)]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Объединяем stderr с stdout
                text=True,
                encoding='utf-8',  # Явно указываем UTF-8 для корректной обработки русских символов
                errors='replace',  # Заменяем проблемные символы вместо ошибки
                bufsize=1,  # Буферизация построчная
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            # Открываем диалог с выводом консоли
            dialog = ProcessOutputDialog(
                self,
                f"Анализ документации ({len(tender_ids_44fz) + len(tender_ids_223fz)} закупок)"
            )
            dialog.start_process(process)
            dialog.show()
            
            logger.info(f"Запущена обработка документов для {len(tender_ids_44fz) + len(tender_ids_223fz)} закупок")
            logger.info(f"Команда: {' '.join(cmd)}")
            
        except Exception as error:
            logger.error(f"Ошибка при запуске обработки документов: {error}")
            logger.exception("Детали ошибки:")
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить анализ документации:\n{error}")
    
    def _run_document_processing_for_all(self, priority_44fz: List[Dict[str, Any]], priority_223fz: List[Dict[str, Any]], registry_type: Optional[str] = None):
        """
        Запуск обработки документов для всех закупок с учетом приоритетных
        
        Args:
            priority_44fz: Приоритетные закупки 44ФЗ
            priority_223fz: Приоритетные закупки 223ФЗ
            registry_type: Тип реестра для анализа ('44fz', '223fz' или None для обоих)
        """
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            # Запускаем скрипт обработки документов БЕЗ конкретных ID
            # Скрипт сам получит все закупки по настройкам пользователя
            # Но мы передадим приоритетные, чтобы они обрабатывались первыми
            # Путь к скрипту: modules/bids/widget.py -> корень проекта -> scripts/run_document_processing.py
            script_path = Path(__file__).parent.parent.parent / "scripts" / "run_document_processing.py"
            
            if not script_path.exists():
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Скрипт обработки документов не найден:\n{script_path}"
                )
                return
            
            # Формируем список приоритетных ID для передачи в скрипт
            priority_tender_ids = []
            if priority_44fz:
                for t in priority_44fz:
                    if t.get('id'):
                        priority_tender_ids.append({'id': t.get('id'), 'registry_type': '44fz'})
            if priority_223fz:
                for t in priority_223fz:
                    if t.get('id'):
                        priority_tender_ids.append({'id': t.get('id'), 'registry_type': '223fz'})
            
            # Если есть приоритетные, передаем их отдельно
            # Скрипт должен обработать сначала приоритетные, затем все остальные
            if priority_tender_ids:
                # Формируем строку аргументов для приоритетных
                tenders_arg_parts = []
                ids_44fz = [t['id'] for t in priority_tender_ids if t.get('registry_type') == '44fz']
                ids_223fz = [t['id'] for t in priority_tender_ids if t.get('registry_type') == '223fz']
                
                if ids_44fz:
                    ids_str = ','.join(map(str, ids_44fz))
                    tenders_arg_parts.append(f"44fz:{ids_str}")
                if ids_223fz:
                    ids_str = ','.join(map(str, ids_223fz))
                    tenders_arg_parts.append(f"223fz:{ids_str}")
                
                tenders_arg = ' '.join(tenders_arg_parts)
                
                # Запускаем скрипт с приоритетными тендерами
                # Скрипт должен сначала обработать их, затем получить все остальные
                cmd = [sys.executable, str(script_path), '--tenders', tenders_arg, '--user-id', str(self.current_user_id), '--all-after-priority']
                if registry_type:
                    cmd.extend(['--registry-type', registry_type])
                dialog_title = f"Анализ всех закупок (приоритетных: {len(priority_tender_ids)})"
            else:
                # Нет приоритетных - просто запускаем обработку всех
                cmd = [sys.executable, str(script_path), '--user-id', str(self.current_user_id)]
                if registry_type:
                    cmd.extend(['--registry-type', registry_type])
                dialog_title = "Анализ всех закупок"
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Объединяем stderr с stdout
                text=True,
                encoding='utf-8',  # Явно указываем UTF-8 для корректной обработки русских символов
                errors='replace',  # Заменяем проблемные символы вместо ошибки
                bufsize=1,  # Буферизация построчная
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            # Открываем диалог с выводом консоли
            dialog = ProcessOutputDialog(self, dialog_title)
            dialog.start_process(process)
            dialog.show()
            
            logger.info(f"Запущена обработка документов для всех закупок (приоритетных: {len(priority_tender_ids)})")
            logger.info(f"Команда: {' '.join(cmd)}")
            
        except Exception as error:
            logger.error(f"Ошибка при запуске обработки документов: {error}")
            logger.exception("Детали ошибки:")
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить анализ документации:\n{error}")
