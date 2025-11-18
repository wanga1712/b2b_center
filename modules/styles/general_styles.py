"""
Единые стили для всего приложения B2B AutoDesk с глобальным масштабированием
"""
from modules.styles.scaling  import scale_size, scale_font_size, get_scale_factor
from config.settings import config

# Получаем глобальный коэффициент масштабирования
SCALE_FACTOR = get_scale_factor()

# Получаем настройки UI из конфигурации
UI_CONFIG = config.ui

# Базовый размер шрифта из конфигурации (если задан)
BASE_FONT_SIZE = UI_CONFIG.font_size if hasattr(UI_CONFIG, 'font_size') and UI_CONFIG.font_size > 0 else 14

# Семейство шрифта из конфигурации
FONT_FAMILY = UI_CONFIG.font_family if hasattr(UI_CONFIG, 'font_family') and UI_CONFIG.font_family else 'Arial'

# Масштабированные размеры шрифтов (относительно базового размера из конфигурации)
FONT_SIZES = {
    'h1': f"{scale_font_size(int(BASE_FONT_SIZE * 1.43))}px",      # Заголовки первого уровня (~20px при базовом 14px)
    'h2': f"{scale_font_size(int(BASE_FONT_SIZE * 1.29))}px",      # Заголовки второго уровня (~18px при базовом 14px)
    'h3': f"{scale_font_size(int(BASE_FONT_SIZE * 1.14))}px",      # Заголовки третьего уровня (~16px при базовом 14px)
    'normal': f"{scale_font_size(BASE_FONT_SIZE)}px",              # Основной текст (базовый размер)
    'small': f"{scale_font_size(int(BASE_FONT_SIZE * 0.86))}px",   # Мелкий текст (~12px при базовом 14px)
    'large': f"{scale_font_size(int(BASE_FONT_SIZE * 1.07))}px",   # Крупный текст (~15px при базовом 14px)
    'xlarge': f"{scale_font_size(int(BASE_FONT_SIZE * 1.21))}px",  # Очень крупный текст (~17px при базовом 14px)
    'xxlarge': f"{scale_font_size(int(BASE_FONT_SIZE * 1.57))}px", # Для заголовков приложения (~22px при базовом 14px)
}

# Масштабированные отступы и размеры
SIZES = {
    'padding_small': scale_size(4),
    'padding_normal': scale_size(6),
    'padding_large': scale_size(10),
    'border_radius_small': scale_size(4),
    'border_radius_normal': scale_size(6),
    'border_radius_large': scale_size(8),
    'border_radius_xlarge': scale_size(12),
    'button_height': scale_size(28),  # Уменьшено с 40 до 28 (текст + 6-8px padding)
    'input_height': scale_size(28),   # Уменьшено для компактности
    'sidebar_width': scale_size(200),
    'topbar_height': scale_size(48),  # Уменьшено с 58
    'table_row_height': scale_size(35),  # Уменьшено с 45
}

# Цветовая палитра Bitrix24
# Принудительно используем цвета Bitrix24, игнорируя конфигурацию для единообразия
COLORS = {
    'primary': '#2066B0',  # Bitrix24 Primary Blue
    'primary_dark': '#1A5490',  # Bitrix24 Dark Blue (для hover состояний)
    'secondary': '#F5F5F5',  # Bitrix24 Light Gray Background
    'white': '#FFFFFF',
    'text_dark': '#535C69',  # Bitrix24 Dark Text
    'text_light': '#828282',  # Bitrix24 Light Text
    'border': '#D5D5D5',  # Bitrix24 Border Color
    'success': '#9ECF00',  # Bitrix24 Success Green
    'warning': '#FFA726',  # Bitrix24 Warning Orange
    'error': '#E53935',  # Bitrix24 Error Red
}

# Стили для кнопок
BUTTON_STYLES = {
    'primary': f"""
        QPushButton {{
            background: {COLORS['primary']};
            color: white;
            border: none;
            border-radius: {SIZES['border_radius_normal']}px;
            padding: 4px 10px;
            font-weight: bold;
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZES['normal']};
            min-height: {SIZES['button_height']}px;
            max-height: {SIZES['button_height']}px;
        }}
        QPushButton:hover {{
            background: {COLORS['primary_dark']};
        }}
        QPushButton:disabled {{
            background: #cccccc;
            color: #666666;
        }}
    """,

    'secondary': f"""
        QPushButton {{
            background: {COLORS['white']};
            color: {COLORS['primary']};
            border: 1px solid {COLORS['primary']};
            border-radius: {SIZES['border_radius_normal']}px;
            padding: 3px 8px;
            font-weight: bold;
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZES['normal']};
            min-height: {SIZES['button_height']}px;
            max-height: {SIZES['button_height']}px;
        }}
        QPushButton:hover {{
            background: {COLORS['primary']};
            color: white;
        }}
    """,

    'outline': f"""
        QPushButton {{
            background: transparent;
            color: {COLORS['text_dark']};
            border: 1px solid {COLORS['border']};
            border-radius: {SIZES['border_radius_small']}px;
            padding: 3px 8px;
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZES['normal']};
            min-height: {SIZES['button_height'] - 4}px;
            max-height: {SIZES['button_height'] - 4}px;
        }}
        QPushButton:hover {{
            background: {COLORS['secondary']};
            border-color: {COLORS['primary']};
        }}
    """
}

# Стили для полей ввода
INPUT_STYLES = {
    'default': f"""
        QLineEdit, QTextEdit, QSpinBox {{
            border: 2px solid {COLORS['border']};
            border-radius: {SIZES['border_radius_small']}px;
            padding: {SIZES['padding_small']}px {SIZES['padding_normal']}px;
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZES['normal']};
            background: {COLORS['white']};
            min-height: {SIZES['input_height']}px;
        }}
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {{
            border-color: {COLORS['primary']};
        }}
    """
}

# Стили для выпадающих списков
COMBOBOX_STYLES = {
    'default': f"""
        QComboBox {{
            border: 2px solid {COLORS['border']};
            border-radius: {SIZES['border_radius_small']}px;
            padding: {SIZES['padding_small']}px {SIZES['padding_normal']}px;
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZES['normal']};
            background: {COLORS['white']};
            min-width: {scale_size(120)}px;
            min-height: {SIZES['input_height']}px;
        }}
        QComboBox:focus {{
            border-color: {COLORS['primary']};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: {scale_size(25)}px;
            border-left: 1px solid {COLORS['border']};
        }}
    """
}

# Стили для меток
LABEL_STYLES = {
    'h1': f"font-family: \"{FONT_FAMILY}\"; font-size: {FONT_SIZES['h1']}; font-weight: bold; color: {COLORS['primary']}; margin-bottom: {scale_size(10)}px;",
    'h2': f"font-family: \"{FONT_FAMILY}\"; font-size: {FONT_SIZES['h2']}; font-weight: bold; color: {COLORS['text_dark']}; margin-bottom: {scale_size(8)}px;",
    'h3': f"font-family: \"{FONT_FAMILY}\"; font-size: {FONT_SIZES['h3']}; font-weight: bold; color: {COLORS['text_dark']}; margin-bottom: {scale_size(6)}px;",
    'normal': f"font-family: \"{FONT_FAMILY}\"; font-size: {FONT_SIZES['normal']}; color: {COLORS['text_dark']};",
    'small': f"font-family: \"{FONT_FAMILY}\"; font-size: {FONT_SIZES['small']}; color: {COLORS['text_light']};",
    'xlarge': f"font-family: \"{FONT_FAMILY}\"; font-size: {FONT_SIZES['xlarge']}; color: {COLORS['text_dark']}; font-weight: bold;",
    'xxlarge': f"font-family: \"{FONT_FAMILY}\"; font-size: {FONT_SIZES['xxlarge']}; color: {COLORS['white']}; font-weight: bold;",
}

# Стили для фреймов
FRAME_STYLES = {
    'card': f"""
        QFrame {{
            background: {COLORS['white']};
            border-radius: {SIZES['border_radius_large']}px;
            border: 1px solid {COLORS['border']};
            padding: {SIZES['padding_large']}px;
        }}
    """,

    'sidebar': f"""
        QFrame {{
            background: {COLORS['secondary']};
            border-right: 1px solid {COLORS['border']};
            min-width: {SIZES['sidebar_width']}px;
        }}
    """
}

# Стили для стекированного виджета
STACKED_STYLES = {
    'default': f"""
        QWidget {{ 
            background: {COLORS['secondary']};
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZES['large']};
        }}
        QTableWidget {{
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZES['large']};
            border-radius: {SIZES['border_radius_normal']}px;
            background: {COLORS['white']};
        }}
        QTableWidget::item {{
            padding: {scale_size(8)}px;
            font-size: {FONT_SIZES['normal']};
        }}
        QHeaderView::section {{
            background: {COLORS['primary']};
            color: white;
            font-weight: bold;
            font-family: "{FONT_FAMILY}";
            padding: {scale_size(10)}px;
            border: none;
            font-size: {FONT_SIZES['normal']};
        }}
        QLineEdit, QTextEdit, QComboBox {{
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZES['large']};
            border-radius: {SIZES['border_radius_normal']}px;
        }}
        QGroupBox, QFrame {{ 
            background: {COLORS['white']};
            border-radius: {SIZES['border_radius_large']}px;
            border: 1px solid {COLORS['border']};
        }}
        QLabel {{ 
            color: {COLORS['text_dark']};
        }}
    """
}

# Стили для сайдбара
SIDEBAR_STYLES = {
    'button': f"""
        QPushButton {{
            color: {COLORS['primary']}; 
            background: none;
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZES['xlarge']}; 
            border: none; 
            padding: {scale_size(18)}px {scale_size(14)}px; 
            text-align: left; 
            border-radius: {SIZES['border_radius_xlarge']}px;
            min-height: {scale_size(50)}px;
        }}
        QPushButton:checked, QPushButton:hover {{
            background: #E3F2FD; 
            color: {COLORS['primary']};
            font-weight: bold; 
        }}
    """
}

# Стили для топбара
TOPBAR_STYLES = {
    'default': f"""
        QFrame {{ 
            background: {COLORS['primary']};
            min-height: {SIZES['topbar_height']}px; 
            border-bottom: 2px solid {COLORS['white']};
        }}
        QLabel {{ 
            color: {COLORS['white']}; 
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZES['xxlarge']}; 
            font-weight: bold;
        }}
    """
}

# Стили для таблиц
TABLE_STYLES = {
    'default': f"""
        QTableWidget {{
            font-family: "{FONT_FAMILY}";
            font-size: {FONT_SIZES['large']};
            border-radius: {SIZES['border_radius_normal']}px;
            background: {COLORS['white']};
            gridline-color: {COLORS['border']};
        }}
        QTableWidget::item {{
            padding: {scale_size(8)}px;
            font-size: {FONT_SIZES['normal']};
            border-bottom: 1px solid {COLORS['border']};
        }}
        QHeaderView::section {{
            background: {COLORS['primary']};
            color: white;
            font-weight: bold;
            font-family: "{FONT_FAMILY}";
            padding: {scale_size(12)}px;
            border: none;
            font-size: {FONT_SIZES['normal']};
        }}
        QTableWidget QAbstractItemView {{
            selection-background-color: {COLORS['primary']};
            selection-color: white;
        }}
    """
}

# Функции для применения стилей
def apply_button_style(widget, style_type='primary'):
    widget.setStyleSheet(BUTTON_STYLES.get(style_type, BUTTON_STYLES['primary']))

def apply_input_style(widget, style_type='default'):
    widget.setStyleSheet(INPUT_STYLES.get(style_type, INPUT_STYLES['default']))

def apply_label_style(widget, style_type='normal'):
    widget.setStyleSheet(LABEL_STYLES.get(style_type, LABEL_STYLES['normal']))

def apply_combobox_style(widget):
    widget.setStyleSheet(COMBOBOX_STYLES['default'])

def apply_frame_style(widget, style_type='card'):
    widget.setStyleSheet(FRAME_STYLES.get(style_type, FRAME_STYLES['card']))

def apply_stacked_style(widget):
    widget.setStyleSheet(STACKED_STYLES['default'])

def apply_sidebar_button_style(widget):
    widget.setStyleSheet(SIDEBAR_STYLES['button'])

def apply_topbar_style(widget):
    widget.setStyleSheet(TOPBAR_STYLES['default'])

def apply_table_style(widget):
    widget.setStyleSheet(TABLE_STYLES['default'])

# Вспомогательные функции для часто используемых стилей (DRY принцип)
def apply_text_color(widget, color_type='text_light'):
    """
    Применение цвета текста к виджету.
    
    Args:
        widget: Виджет (QLabel, QPushButton и т.д.)
        color_type: Тип цвета ('text_light', 'text_dark', 'primary', 'error', 'success', 'warning')
    """
    color = COLORS.get(color_type, COLORS['text_light'])
    current_style = widget.styleSheet() or ""
    widget.setStyleSheet(f"{current_style} color: {color};")

def apply_font_weight(widget, weight='600'):
    """
    Применение жирности шрифта к виджету.
    
    Args:
        widget: Виджет
        weight: Вес шрифта ('600', 'bold', 'normal')
    """
    current_style = widget.styleSheet() or ""
    widget.setStyleSheet(f"{current_style} font-weight: {weight};")

def apply_text_style_light(widget):
    """Быстрое применение стиля светлого текста."""
    apply_text_color(widget, 'text_light')

def apply_text_style_dark(widget):
    """Быстрое применение стиля темного текста."""
    apply_text_color(widget, 'text_dark')

def apply_text_style_primary(widget):
    """Быстрое применение стиля основного цвета."""
    apply_text_color(widget, 'primary')

def apply_text_style_light_italic(widget):
    """
    Применение стиля светлого текста с курсивом (для информационных сообщений).
    
    Args:
        widget: Виджет
    """
    current_style = widget.styleSheet() or ""
    widget.setStyleSheet(f"{current_style} color: {COLORS['text_light']}; font-style: italic;")

# Функция для получения информации о масштабировании
def get_scaling_info():
    return {
        'scale_factor': SCALE_FACTOR,
        'font_sizes': FONT_SIZES,
        'sizes': SIZES
    }