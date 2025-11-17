"""
Стили для таблиц и элементов внутри таблиц

Содержит стили для:
- Таблиц (QTableWidget)
- Кнопок внутри таблиц
- Ячеек таблиц
"""

from modules.styles.general_styles import (
    COLORS, FONT_SIZES, SIZES, scale_size
)


def get_table_button_style() -> str:
    """
    Стиль для кнопок внутри таблиц (компактный, без лишних отступов)
    
    Returns:
        Строка со стилями CSS для QPushButton в таблицах
    """
    return f"""
        QPushButton {{
            background: transparent;
            color: {COLORS['text_dark']};
            border: 1px solid {COLORS['border']};
            border-radius: {SIZES['border_radius_small']}px;
            padding: 2px 6px;
            margin: 0px;
            font-size: {FONT_SIZES['normal']};
            min-height: {SIZES['button_height'] - 6}px;
            max-height: {SIZES['button_height'] - 6}px;
        }}
        QPushButton:hover {{
            background: {COLORS['secondary']};
            border-color: {COLORS['primary']};
        }}
    """


def get_table_cell_widget_container_style() -> str:
    """
    Стиль для контейнеров виджетов внутри ячеек таблиц
    
    Returns:
        Строка со стилями CSS для контейнеров в ячейках таблиц
    """
    return "background: transparent; margin: 0px; padding: 0px;"


def get_table_style() -> str:
    """
    Базовый стиль для таблиц
    
    Returns:
        Строка со стилями CSS для QTableWidget
    """
    return f"""
        QTableWidget {{
            font-size: {FONT_SIZES['normal']};
            border-radius: 6px;
            background: {COLORS['white']};
        }}
        QTableWidget::item {{
            padding: 4px;
        }}
        QHeaderView::section {{
            background: {COLORS['primary']};
            color: white;
            font-weight: bold;
            padding: 6px;
            border: none;
            font-size: {FONT_SIZES['small']};
        }}
    """

