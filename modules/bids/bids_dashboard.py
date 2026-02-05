"""
MODULE: modules.bids.bids_dashboard
RESPONSIBILITY: Main dashboard UI with tiles and statistics.
ALLOWED: PyQt5, typing, modules.styles.
FORBIDDEN: Logical processing (should be in managers).
ERRORS: None.

Dashboard закупок в стиле Windows 11 + Salesforce.
Начальная страница с плитками разделов и статистикой.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QGridLayout, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Dict, Any, Callable, Optional
from modules.styles.general_styles import COLORS, SIZES, FONT_SIZES


class BidsTile(QFrame):
    """Плитка раздела закупок (Windows 11 style)."""
    
    clicked = pyqtSignal(str)  # section_id
    
    def __init__(
        self,
        section_id: str,
        title: str,
        icon: str,
        description: str,
        count: Optional[int] = None,
        color: str = "#0078D4",
        parent=None
    ):
        super().__init__(parent)
        self.section_id = section_id
        self.title = title
        self.icon = icon
        self.count = count
        self.color = color
        
        self.setFixedSize(280, 180)
        self.setCursor(Qt.PointingHandCursor)
        self.setVisible(True)  # Явно устанавливаем видимость карточки
        self.init_ui(description)
    
    def init_ui(self, description: str):
        """Инициализация UI плитки."""
        # Сохраняем описание для возможного перерисовывания
        self._last_description = description
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Иконка
        icon_label = QLabel(self.icon)
        icon_font = QFont()
        icon_font.setPointSize(48)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignLeft)
        icon_label.setVisible(True)  # Явно устанавливаем видимость
        layout.addWidget(icon_label)
        
        layout.addStretch()
        
        # Название
        title_label = QLabel(self.title)
        title_label.setStyleSheet(
            f"font-size: {FONT_SIZES['large']}; font-weight: bold; color: {COLORS['text_dark']};"
        )
        title_label.setWordWrap(True)
        title_label.setVisible(True)  # Явно устанавливаем видимость
        layout.addWidget(title_label)
        
        # Описание
        desc_label = QLabel(description)
        desc_label.setStyleSheet(
            f"font-size: {FONT_SIZES['small']}; color: {COLORS['text_light']};"
        )
        desc_label.setWordWrap(True)
        desc_label.setVisible(True)  # Явно устанавливаем видимость
        layout.addWidget(desc_label)
        
        # Счетчик (показываем всегда, если count не None)
        # Сохраняем ссылку на count_label для возможного обновления
        if self.count is not None:
            count_text = f"{self.count} закупок" if self.count > 0 else "Нет закупок"
            count_label = QLabel(count_text)
            count_label.setStyleSheet(
                f"""
                font-size: {FONT_SIZES['normal']};
                font-weight: bold;
                color: {self.color};
                background: {self.color}22;
                padding: 4px 12px;
                border-radius: {SIZES['border_radius_small']}px;
                """
            )
            count_label.setFixedWidth(120)
            count_label.setVisible(True)
            layout.addWidget(count_label)
            # Сохраняем ссылку для обновления
            self._count_label = count_label
        else:
            self._count_label = None
        
        self._apply_tile_style()
    
    def _apply_tile_style(self):
        """Применить Windows 11 стиль плитки."""
        # Применяем стиль напрямую к QFrame, но убеждаемся, что дочерние элементы видимы
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {COLORS['white']};
                border: 2px solid {COLORS['border']};
                border-left: 4px solid {self.color};
                border-radius: {SIZES['border_radius_normal']}px;
            }}
            QFrame:hover {{
                background: {COLORS['secondary']};
                border-left: 6px solid {self.color};
                box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
            }}
            QLabel {{
                background: transparent;
            }}
            """
        )
        # Убеждаемся, что карточка и все дочерние элементы видимы
        self.setVisible(True)
        self.show()  # Принудительно показываем карточку
    
    def mousePressEvent(self, event):
        """Обработка клика по плитке."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.section_id)
        super().mousePressEvent(event)
    
    def update_count(self, count: int):
        """Обновить счетчик закупок."""
        self.count = count
        
        # Обновляем счетчик, если он уже существует
        if hasattr(self, '_count_label') and self._count_label is not None:
            count_text = f"{count} закупок" if count > 0 else "Нет закупок"
            self._count_label.setText(count_text)
            self._count_label.setVisible(True)
        else:
            # Если счетчика нет, добавляем его в layout
            if hasattr(self, '_last_description'):
                description = self._last_description
            else:
                description = ""
            
            # Находим последний элемент в layout (обычно это stretch или последний виджет)
            layout = self.layout()
            if layout:
                count_text = f"{count} закупок" if count > 0 else "Нет закупок"
                count_label = QLabel(count_text)
                count_label.setStyleSheet(
                    f"""
                    font-size: {FONT_SIZES['normal']};
                    font-weight: bold;
                    color: {self.color};
                    background: {self.color}22;
                    padding: 4px 12px;
                    border-radius: {SIZES['border_radius_small']}px;
                    """
                )
                count_label.setFixedWidth(120)
                count_label.setVisible(True)
                layout.addWidget(count_label)
                self._count_label = count_label


class BidsStatsCard(QFrame):
    """Карточка статистики (Salesforce style)."""
    
    def __init__(self, title: str, value: str, icon: str, color: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 120)
        self.value_label = None  # Для обновления значения
        self.color = color
        self.init_ui(title, value, icon, color)

    def update_value(self, new_value: str):
        """Обновление значения в карточке."""
        if self.value_label:
            self.value_label.setText(new_value)

    def init_ui(self, title: str, value: str, icon: str, color: str):
        """Инициализация UI карточки статистики."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # Верхняя строка: иконка + значение
        top_row = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_font = QFont()
        icon_font.setPointSize(24)
        icon_label.setFont(icon_font)
        top_row.addWidget(icon_label)
        
        top_row.addStretch()
        
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            f"font-size: {FONT_SIZES['h1']}; font-weight: bold; color: {self.color};"
        )
        top_row.addWidget(self.value_label)
        
        layout.addLayout(top_row)
        
        layout.addStretch()
        
        # Название метрики
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"font-size: {FONT_SIZES['normal']}; color: {COLORS['text_light']};"
        )
        layout.addWidget(title_label)
        
        self.setStyleSheet(
            f"""
            BidsStatsCard {{
                background: {COLORS['white']};
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
            }}
            BidsStatsCard:hover {{
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }}
            """
        )


class BidsDashboard(QWidget):
    """Dashboard закупок - начальная страница с плитками."""
    
    section_selected = pyqtSignal(str)  # section_id
    settings_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tiles = []
        self.stats_cards = []
        self.init_ui()
    
    def init_ui(self):
        """Инициализация UI dashboard."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Скроллируемая область
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        # Исправление: используем 'secondary' вместо несуществующего 'background'
        background_color = COLORS.get('background', COLORS.get('secondary', '#F5F5F5'))
        scroll_area.setStyleSheet(
            f"QScrollArea {{ border: none; background: {background_color}; }}"
        )
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(30)
        
        # Заголовок
        header_layout = self._create_header()
        container_layout.addLayout(header_layout)
        
        # Статистика (Salesforce style)
        stats_layout = self._create_stats_section()
        container_layout.addLayout(stats_layout)
        
        # Плитки разделов (Windows 11 style)
        tiles_layout = self._create_tiles_section()
        container_layout.addLayout(tiles_layout)
        
        container_layout.addStretch()
        
        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

    def update_filtering_stats(self, okpd_filtered: int, okpd_total: int, stop_words_filtered: int, stop_words_total: int):
        """
        Обновление статистики фильтрации.

        Args:
            okpd_filtered: Количество торгов после фильтра OKPD
            okpd_total: Общее количество торгов до фильтра OKPD
            stop_words_filtered: Количество торгов после фильтра стоп-слов
            stop_words_total: Общее количество торгов до фильтра стоп-слов
        """
        try:
            # Обновляем карточку "Фильтр OKPD"
            if len(self.stats_cards) > 4:
                okpd_card = self.stats_cards[4]  # 5-я карточка
                okpd_card.update_value(f"{okpd_filtered}/{okpd_total}")

            # Обновляем карточку "Фильтр стоп-слов"
            if len(self.stats_cards) > 5:
                stop_words_card = self.stats_cards[5]  # 6-я карточка
                stop_words_card.update_value(f"{stop_words_filtered}/{stop_words_total}")

        except Exception as e:
            print(f"Ошибка обновления статистики фильтрации: {e}")

    def _create_header(self) -> QHBoxLayout:
        """Создание заголовка dashboard."""
        header_layout = QHBoxLayout()
        
        # Заголовок
        title_layout = QVBoxLayout()
        title_label = QLabel("📈 Управление закупками")
        title_label.setStyleSheet(
            f"font-size: {FONT_SIZES['h1']}; font-weight: bold; color: {COLORS['text_dark']};"
        )
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Закупки 44ФЗ и 223ФЗ • Анализ документации • Управление")
        subtitle_label.setStyleSheet(
            f"font-size: {FONT_SIZES['normal']}; color: {COLORS['text_light']};"
        )
        title_layout.addWidget(subtitle_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Кнопка настроек
        settings_btn = QPushButton("⚙️ Настройки")
        settings_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS['white']};
                color: {COLORS['text_dark']};
                border: 2px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_small']}px;
                padding: 10px 20px;
                font-size: {FONT_SIZES['normal']};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLORS['secondary']};
                border-color: {COLORS['primary']};
            }}
            """
        )
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.clicked.connect(self.settings_clicked.emit)
        header_layout.addWidget(settings_btn)
        
        return header_layout
    
    def _create_stats_section(self) -> QHBoxLayout:
        """Создание секции статистики (Salesforce style)."""
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        # Карточки статистики
        stats_data = [
            ("Всего закупок", "0", "📊", COLORS['primary']),
            ("В работе", "0", "⚡", "#ffc107"),
            ("Обработано", "0", "✓", "#28a745"),
            ("Новых", "0", "🔔", "#17a2b8"),
        ]
        
        for title, value, icon, color in stats_data:
            card = BidsStatsCard(title, value, icon, color)
            self.stats_cards.append(card)
            stats_layout.addWidget(card)
        
        stats_layout.addStretch()
        
        return stats_layout
    
    def _create_tiles_section(self) -> QVBoxLayout:
        """Создание секции с плитками разделов (Windows 11 style)."""
        tiles_layout = QVBoxLayout()
        tiles_layout.setSpacing(20)
        
        # Заголовок секции
        section_label = QLabel("Разделы закупок")
        section_label.setStyleSheet(
            f"font-size: {FONT_SIZES['h2']}; font-weight: bold; color: {COLORS['text_dark']};"
        )
        tiles_layout.addWidget(section_label)
        
        # Сетка плиток
        grid = QGridLayout()
        grid.setSpacing(20)
        
        # Данные плиток
        tiles_data = [
            ("purchases_44fz_new", "Новые 44ФЗ", "📋", "Актуальные закупки 44ФЗ", "#0078D4"),
            ("purchases_223fz_new", "Новые 223ФЗ", "📄", "Актуальные закупки 223ФЗ", "#00BCF2"),
            ("purchases_44fz_won", "Разыгранные 44ФЗ", "🏆", "Разыгранные закупки 44ФЗ", "#28a745"),
            ("purchases_223fz_won", "Разыгранные 223ФЗ", "🎯", "Разыгранные закупки 223ФЗ", "#20c997"),
            ("purchases_44fz_commission", "Работа комиссии", "👥", "Закупки на стадии комиссии", "#ffc107"),
            ("purchases_in_work", "В работе", "⚙️", "Закупки в процессе обработки", "#6f42c1"),
        ]
        
        row, col = 0, 0
        for section_id, title, icon, desc, color in tiles_data:
            # Инициализируем с None, чтобы счетчик не показывался до обновления
            tile = BidsTile(section_id, title, icon, desc, None, color)
            tile.clicked.connect(self.section_selected.emit)
            self.tiles.append(tile)
            grid.addWidget(tile, row, col)
            
            col += 1
            if col >= 3:  # 3 плитки в ряду
                col = 0
                row += 1
        
        tiles_layout.addLayout(grid)
        
        return tiles_layout
    
    def update_tile_count(self, section_id: str, count: int):
        """Обновить счетчик закупок на плитке."""
        for tile in self.tiles:
            if tile.section_id == section_id:
                tile.update_count(count)
                break
    
    def update_stats(self, stats: Dict[str, Any]):
        """
        Обновить статистику.
        
        Args:
            stats: словарь с ключами 'total', 'in_work', 'processed', 'new'
        """
        if len(self.stats_cards) >= 4:
            self.stats_cards[0].findChild(QLabel).setText(str(stats.get('total', 0)))
            self.stats_cards[1].findChild(QLabel).setText(str(stats.get('in_work', 0)))
            self.stats_cards[2].findChild(QLabel).setText(str(stats.get('processed', 0)))
            self.stats_cards[3].findChild(QLabel).setText(str(stats.get('new', 0)))

