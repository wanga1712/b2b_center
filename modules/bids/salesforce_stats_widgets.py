"""
MODULE: modules.bids.salesforce_stats_widgets
RESPONSIBILITY: Widgets for displaying statistics in Salesforce style.
ALLOWED: PyQt5, modules.styles.
FORBIDDEN: Data fetching/processing.
ERRORS: None.

Виджеты статистики в стиле Salesforce с прогресс-индикаторами.
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPainter, QColor, QPen
from modules.styles.general_styles import COLORS, SIZES, FONT_SIZES


class CircularProgressWidget(QWidget):
    """Круговой прогресс-индикатор (как спидометр в Salesforce)."""
    
    def __init__(self, value: int, max_value: int, color: str, parent=None):
        super().__init__(parent)
        self.value = value
        self.max_value = max_value
        self.color = color
        self.setFixedSize(80, 80)
    
    def paintEvent(self, event):
        """Отрисовка кругового индикатора."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Фоновый круг (серый)
        painter.setPen(QPen(QColor(COLORS['border']), 6))
        painter.drawArc(10, 10, 60, 60, 0, 360 * 16)
        
        # Прогресс-круг (цветной)
        if self.max_value > 0:
            progress_angle = int((self.value / self.max_value) * 360 * 16)
            painter.setPen(QPen(QColor(self.color), 6))
            painter.drawArc(10, 10, 60, 60, 90 * 16, -progress_angle)
        
        # Процент в центре
        painter.setPen(QPen(QColor(COLORS['text_dark'])))
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        
        if self.max_value > 0:
            percent = int((self.value / self.max_value) * 100)
            painter.drawText(10, 10, 60, 60, Qt.AlignCenter, f"{percent}%")
        else:
            painter.drawText(10, 10, 60, 60, Qt.AlignCenter, "0%")


class SalesforceStatsCard(QFrame):
    """Карточка статистики в стиле Salesforce с прогресс-индикатором."""
    
    def __init__(
        self,
        title: str,
        value: int,
        max_value: int,
        icon: str,
        color: str,
        show_progress: bool = True,
        parent=None
    ):
        """
        Args:
            title: Название метрики
            value: Текущее значение
            max_value: Максимальное значение (для прогресса)
            icon: Эмодзи-иконка
            color: Цвет акцента
            show_progress: Показывать прогресс-бар
        """
        super().__init__(parent)
        self.title = title
        self.value = value
        self.max_value = max_value
        self.icon = icon
        self.color = color
        self.show_progress = show_progress
        
        self.setFixedSize(240, 160)
        self.init_ui()
    
    def init_ui(self):
        """Инициализация UI карточки."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Заголовок с иконкой
        header_layout = QHBoxLayout()
        
        icon_label = QLabel(self.icon)
        icon_font = QFont()
        icon_font.setPointSize(20)
        icon_label.setFont(icon_font)
        header_layout.addWidget(icon_label)
        
        title_label = QLabel(self.title)
        title_label.setStyleSheet(
            f"font-size: {FONT_SIZES['normal']}; color: {COLORS['text_light']}; font-weight: bold;"
        )
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Значение
        value_label = QLabel(str(self.value))
        value_label.setStyleSheet(
            f"font-size: {FONT_SIZES['h1']}; font-weight: bold; color: {self.color};"
        )
        value_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(value_label)
        
        # Прогресс-бар (Salesforce style) или круговой индикатор
        if self.show_progress and self.max_value > 0:
            progress_layout = QHBoxLayout()
            
            # Горизонтальный прогресс-бар
            progress_bar = QProgressBar()
            progress_bar.setRange(0, self.max_value)
            progress_bar.setValue(self.value)
            progress_bar.setTextVisible(False)
            progress_bar.setFixedHeight(8)
            progress_bar.setStyleSheet(
                f"""
                QProgressBar {{
                    background: {COLORS['secondary']};
                    border: none;
                    border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background: {self.color};
                    border-radius: 4px;
                }}
                """
            )
            progress_layout.addWidget(progress_bar)
            
            # Процент
            if self.max_value > 0:
                percent = int((self.value / self.max_value) * 100)
                percent_label = QLabel(f"{percent}%")
                percent_label.setStyleSheet(
                    f"font-size: {FONT_SIZES['small']}; color: {COLORS['text_light']}; font-weight: bold;"
                )
                percent_label.setFixedWidth(40)
                progress_layout.addWidget(percent_label)
            
            layout.addLayout(progress_layout)
        
        layout.addStretch()
        
        # Стиль карточки
        self.setStyleSheet(
            f"""
            SalesforceStatsCard {{
                background: {COLORS['white']};
                border: 1px solid {COLORS['border']};
                border-left: 4px solid {self.color};
                border-radius: {SIZES['border_radius_normal']}px;
            }}
            SalesforceStatsCard:hover {{
                box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
                border-left-width: 6px;
            }}
            """
        )
    
    def update_value(self, value: int, max_value: int = None):
        """Обновить значение карточки."""
        self.value = value
        if max_value is not None:
            self.max_value = max_value
        
        # Перерисовать UI
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            del item
        
        self.init_ui()


class SalesforceGaugeCard(QFrame):
    """Карточка со спидометром (gauge chart) в стиле Salesforce."""
    
    def __init__(
        self,
        title: str,
        value: int,
        max_value: int,
        icon: str,
        color: str,
        parent=None
    ):
        super().__init__(parent)
        self.title = title
        self.value = value
        self.max_value = max_value
        self.icon = icon
        self.color = color
        
        self.setFixedSize(200, 180)
        self.init_ui()
    
    def init_ui(self):
        """Инициализация UI карточки со спидометром."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Заголовок
        title_label = QLabel(self.title)
        title_label.setStyleSheet(
            f"font-size: {FONT_SIZES['normal']}; color: {COLORS['text_light']}; font-weight: bold;"
        )
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Круговой прогресс-индикатор
        circular_progress = CircularProgressWidget(
            value=self.value,
            max_value=self.max_value,
            color=self.color
        )
        layout.addWidget(circular_progress, alignment=Qt.AlignCenter)
        
        # Значение с иконкой
        value_layout = QHBoxLayout()
        
        icon_label = QLabel(self.icon)
        icon_font = QFont()
        icon_font.setPointSize(18)
        icon_label.setFont(icon_font)
        value_layout.addWidget(icon_label)
        
        value_label = QLabel(str(self.value))
        value_label.setStyleSheet(
            f"font-size: {FONT_SIZES['h2']}; font-weight: bold; color: {self.color};"
        )
        value_layout.addWidget(value_label)
        
        value_layout.addStretch()
        
        layout.addLayout(value_layout)
        
        # Стиль карточки
        self.setStyleSheet(
            f"""
            SalesforceGaugeCard {{
                background: {COLORS['white']};
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
            }}
            SalesforceGaugeCard:hover {{
                box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
            }}
            """
        )

