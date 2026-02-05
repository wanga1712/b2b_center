"""
MODULE: modules.crm.info_panel
RESPONSIBILITY: Display the right-side information panel.
ALLOWED: PyQt5, typing, modules.styles.general_styles.
FORBIDDEN: Complex business logic.
ERRORS: None.

Информационная панель (InfoPanel) для правой стороны интерфейса

Отображает контекстную информацию, статистику, быстрые действия и уведомления.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt
from typing import Optional

from modules.styles.general_styles import (
    apply_label_style, apply_frame_style, COLORS, SIZES, FONT_SIZES
)


class InfoPanel(QWidget):
    """
    Информационная панель справа от основного контента
    
    Показывает контекстную информацию в зависимости от текущего раздела.
    """
    
    def __init__(self, parent=None):
        """
        Инициализация информационной панели
        
        Args:
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.setFixedWidth(300)  # Фиксированная ширина панели
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Стиль панели
        self.setStyleSheet(f"""
            QWidget {{
                background: {COLORS['white']};
                border-left: 1px solid {COLORS['border']};
            }}
        """)
        
        # Область прокрутки
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        # Контейнер для контента
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок панели
        header = QLabel("ℹ️ Информация")
        apply_label_style(header, 'h2')
        header.setStyleSheet(f"color: {COLORS['primary']}; margin-bottom: {SIZES['padding_large']}px;")
        content_layout.addWidget(header)
        
        # Блок статистики
        stats_frame = QFrame()
        apply_frame_style(stats_frame, 'card')
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(15, 15, 15, 15)
        
        stats_title = QLabel("📊 Статистика")
        apply_label_style(stats_title, 'h3')
        stats_layout.addWidget(stats_title)
        
        # Пример статистики (будет обновляться динамически)
        self.stats_label = QLabel("Загрузка данных...")
        apply_label_style(self.stats_label, 'small')
        stats_layout.addWidget(self.stats_label)
        
        content_layout.addWidget(stats_frame)
        
        # Блок быстрых действий
        actions_frame = QFrame()
        apply_frame_style(actions_frame, 'card')
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(15, 15, 15, 15)
        
        actions_title = QLabel("⚡ Быстрые действия")
        apply_label_style(actions_title, 'h3')
        actions_layout.addWidget(actions_title)
        
        # Пример быстрых действий (будет обновляться динамически)
        self.actions_label = QLabel("Доступные действия появятся здесь")
        apply_label_style(self.actions_label, 'small')
        actions_layout.addWidget(self.actions_label)
        
        content_layout.addWidget(actions_frame)
        
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
    
    def update_context(self, context_type: str, data: Optional[dict] = None):
        """
        Обновление контекстной информации
        
        Args:
            context_type: Тип контекста (например, 'crm_home', 'purchases', и т.д.)
            data: Данные для отображения
        """
        if context_type == 'crm_home':
            self.stats_label.setText("Выберите раздел для просмотра статистики")
            self.actions_label.setText("Кликните на папку для перехода в раздел")
        else:
            self.stats_label.setText(f"Контекст: {context_type}")
            self.actions_label.setText("Доступные действия появятся здесь")

