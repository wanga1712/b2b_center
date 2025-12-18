"""
Карточка папки для отображения в grid layout

Используется в главном меню CRM и подменю.
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QMovie
from pathlib import Path
from typing import Optional
from loguru import logger

from modules.styles.general_styles import (
    apply_label_style, COLORS, SIZES, FONT_SIZES
)


class FolderCard(QFrame):
    """Карточка папки для отображения в grid layout"""
    
    clicked = pyqtSignal(str)  # Сигнал при клике на папку
    
    def __init__(self, folder_id: str, name: str, icon: str, description: Optional[str] = None, count: Optional[int] = None, icon_path: Optional[str] = None):
        """
        Инициализация карточки папки
        
        Args:
            folder_id: Уникальный идентификатор папки
            name: Название папки
            icon: Эмодзи-иконка или текст иконки (используется если icon_path не указан)
            description: Описание папки (опционально)
            count: Количество элементов в папке (опционально)
            icon_path: Путь к файлу иконки (опционально, приоритет над icon)
        """
        super().__init__()
        self.folder_id = folder_id
        self.name = name
        self.icon = icon
        self.icon_path = icon_path
        self.description = description
        self.count = count
        self._selected = False
        self._hovered = False
        self.movie: Optional[QMovie] = None
        
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui()
        self.update_style()
    
    def init_ui(self):
        """Инициализация интерфейса карточки"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        
        # Компактные размеры в стиле "иконок Windows"
        self.setMinimumSize(160, 170)
        self.setMaximumSize(200, 200)
        
        # Стиль карточки папки задаётся динамически (hover/selected) в update_style()
        
        # Иконка (фиксированный размер 72x72 по центру, увеличен на 10%)
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setMinimumSize(72, 72)
        self.icon_label.setMaximumSize(72, 72)
        
        if self.icon_path and Path(self.icon_path).exists():
            # Проверяем, это GIF или PNG
            if self.icon_path.lower().endswith('.gif'):
                # Используем QMovie для анимации
                self.movie = QMovie(self.icon_path)
                self.movie.setScaledSize(QSize(72, 72))
                self.icon_label.setMovie(self.movie)
                # Анимация запускается при hover (в enterEvent/leaveEvent)
                self.movie.stop()  # Начинаем с остановленной анимации
            else:
                # Используем статичное изображение
                pixmap = QPixmap(self.icon_path)
                scaled_pixmap = pixmap.scaled(
                    72, 72,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.icon_label.setPixmap(scaled_pixmap)
                self.icon_label.setScaledContents(False)
        else:
            # Используем эмодзи или текст
            self.icon_label.setText(self.icon)
            self.icon_label.setStyleSheet("""
                font-size: 42px;
                padding: 4px;
            """)
        
        layout.addWidget(self.icon_label, alignment=Qt.AlignHCenter)
        
        # Название (по центру, как подпись под иконкой)
        name_label = QLabel(self.name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        apply_label_style(name_label, 'h3')
        name_label.setStyleSheet(f"""
            font-weight: bold;
            color: {COLORS['text_dark']};
            margin-top: 6px;
        """)
        layout.addWidget(name_label)
        
        # Счётчик (показываем всегда, placeholder "0" пока нет данных)
        self.count_label = QLabel(str(self.count) if self.count is not None else "0")
        self.count_label.setAlignment(Qt.AlignCenter)
        apply_label_style(self.count_label, 'small')
        self.count_label.setStyleSheet(f"""
            color: {COLORS['primary']};
            font-weight: bold;
            margin-top: 6px;
        """)
        layout.addWidget(self.count_label)
        
        # Подпись/описание не выводим, чтобы было ближе к виду Windows-иконок
        layout.addStretch()
    
    def update_style(self):
        """Обновление стиля карточки с учетом hover/selected"""
        radius = SIZES['border_radius_large']
        # Уменьшаем отступы для более компактных карточек
        pad_v = SIZES.get('padding_small', 4)
        pad_h = SIZES.get('padding_small', 4)
        
        # Градиент убираем с карточки — фон будет на контейнере.
        background = "transparent"
        border = "transparent"
        self.setStyleSheet(f"""
            QFrame {{
                background: {background};
                border: 1px solid {border};
                border-radius: {radius}px;
                padding: {pad_v}px {pad_h}px;
            }}
        """)
    
    def enterEvent(self, event):
        """Обработка входа курсора (hover) - запускаем анимацию GIF если есть"""
        self._hovered = True
        if self.movie:
            self.movie.start()
        self.update_style()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Обработка выхода курсора - останавливаем анимацию GIF если есть"""
        self._hovered = False
        if self.movie:
            self.movie.stop()
            # Возвращаемся к первому кадру
            if self.movie.frameCount() > 0:
                self.movie.jumpToFrame(0)
        self.update_style()
        super().leaveEvent(event)
    
    def update_count(self, count: Optional[int]):
        """Обновление счетчика"""
        if self.count_label:
            self.count_label.setText(str(count) if count is not None else "0")
        self.count = count
    
    def mousePressEvent(self, event):
        """Обработка клика на карточку"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.folder_id)
        super().mousePressEvent(event)
    
    def set_selected(self, selected: bool):
        """Установка выбранного состояния карточки"""
        self._selected = selected
        self.update_style()

