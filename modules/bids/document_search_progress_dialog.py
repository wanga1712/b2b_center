"""
Диалоговое окно с прогресс-баром для отображения процесса поиска по документации
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from typing import Optional
from loguru import logger

from modules.styles.general_styles import (
    COLORS, FONT_SIZES, SIZES, apply_label_style, apply_button_style,
    apply_text_style_light, apply_text_style_dark
)
from modules.styles.ui_config import configure_dialog


class DocumentSearchProgressDialog(QDialog):
    """
    Диалоговое окно с прогресс-баром для отображения процесса поиска по документации.
    
    Отображает этапы:
    1. Скачивание документов
    2. Извлечение данных
    3. Сверка с данными из БД
    """
    
    cancelled = pyqtSignal()  # Сигнал отмены операции
    
    def __init__(self, parent=None):
        super().__init__(parent)
        configure_dialog(self, "Поиск по документации", size_preset="progress_dialog")
        self.setModal(True)
        self._cancelled = False
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса диалога"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title_label = QLabel("Обработка документов...")
        apply_label_style(title_label, 'h2')
        apply_text_style_dark(title_label)
        title_label.setStyleSheet(title_label.styleSheet() + " margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Текущий этап
        self.stage_label = QLabel("Подготовка...")
        apply_label_style(self.stage_label, 'normal')
        apply_text_style_light(self.stage_label)
        self.stage_label.setStyleSheet(self.stage_label.styleSheet() + " margin-bottom: 5px;")
        layout.addWidget(self.stage_label)
        
        # Общий прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
                background: {COLORS['secondary']};
                text-align: center;
                height: 25px;
            }}
            QProgressBar::chunk {{
                background: {COLORS['primary']};
                border-radius: {SIZES['border_radius_normal']}px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # Детальная информация
        self.detail_label = QLabel("")
        apply_label_style(self.detail_label, 'small')
        apply_text_style_light(self.detail_label)
        self.detail_label.setStyleSheet(self.detail_label.styleSheet() + " margin-top: 5px;")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)
        
        # Кнопка отмены
        self.cancel_button = QPushButton("Отменить")
        apply_button_style(self.cancel_button, 'secondary')
        self.cancel_button.clicked.connect(self._on_cancel)
        layout.addWidget(self.cancel_button)
    
    def _on_cancel(self):
        """Обработка нажатия кнопки отмены"""
        self._cancelled = True
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Отмена...")
        self.cancelled.emit()
        logger.info("Пользователь отменил операцию поиска по документации")
    
    def is_cancelled(self) -> bool:
        """Проверка, была ли операция отменена"""
        return self._cancelled
    
    def set_stage(self, stage_name: str, progress: int = 0, detail: Optional[str] = None):
        """
        Установка текущего этапа и прогресса
        
        Args:
            stage_name: Название этапа
            progress: Прогресс в процентах (0-100)
            detail: Детальная информация о текущей операции
        """
        # Ограничиваем прогресс в диапазоне 0-100
        progress = max(0, min(100, progress))
        
        logger.debug(f"Диалог прогресса: {stage_name} - {progress}% - {detail or ''}")
        
        self.stage_label.setText(stage_name)
        self.progress_bar.setValue(progress)
        
        if detail:
            self.detail_label.setText(detail)
        else:
            self.detail_label.setText("")
        
        # Обновляем интерфейс (обрабатываем события для обновления UI)
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
    
    def set_download_progress(self, current: int, total: int, file_name: Optional[str] = None):
        """
        Установка прогресса скачивания
        
        Args:
            current: Номер текущего файла
            total: Общее количество файлов
            file_name: Имя текущего скачиваемого файла
        """
        progress = int((current / total) * 100) if total > 0 else 0
        stage_text = f"Скачивание документов ({current}/{total})"
        detail_text = f"Скачиваю: {file_name}" if file_name else ""
        self.set_stage(stage_text, progress, detail_text)
    
    def set_extraction_progress(self, current: int, total: int, file_name: Optional[str] = None):
        """
        Установка прогресса извлечения данных
        
        Args:
            current: Номер текущего файла
            total: Общее количество файлов
            file_name: Имя текущего обрабатываемого файла
        """
        progress = int((current / total) * 100) if total > 0 else 0
        stage_text = f"Извлечение данных ({current}/{total})"
        detail_text = f"Обрабатываю: {file_name}" if file_name else ""
        self.set_stage(stage_text, progress, detail_text)
    
    def set_search_progress(self, progress: int, detail: Optional[str] = None):
        """
        Установка прогресса сверки с данными из БД
        
        Args:
            progress: Прогресс в процентах (0-100)
            detail: Детальная информация
        """
        self.set_stage("Сверка с данными из БД", progress, detail or "Поиск совпадений...")

