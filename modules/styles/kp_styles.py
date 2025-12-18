"""
Специализированные стили для интерфейса коммерческих предложений (KP).
"""

from modules.styles.general_styles import COLORS, SIZES, FONT_SIZES


KP_INFO_FRAME_STYLE = f"""
    QFrame {{
        background: {COLORS['secondary']};
        border-radius: {SIZES['border_radius_small']}px;
        padding: {SIZES['padding_normal']}px;
        border: 1px solid {COLORS['border']};
    }}
"""

KP_TOTAL_FRAME_STYLE = f"""
    QFrame {{
        background: {COLORS['primary']};
        border-radius: {SIZES['border_radius_normal']}px;
        padding: {SIZES['padding_large']}px {SIZES['padding_large'] * 2}px;
    }}
"""

KP_WIDGET_STYLE = f"""
    QWidget {{
        background: {COLORS['secondary']};
        font-size: {FONT_SIZES['normal']};
    }}
    QTableWidget {{
        font-size: {FONT_SIZES['normal']};
        border-radius: {SIZES['border_radius_small']}px;
        background: {COLORS['white']};
    }}
    QTableWidget::item {{
        padding: {SIZES['padding_small']}px;
    }}
    QHeaderView::section {{
        background: {COLORS['primary']};
        color: {COLORS['white']};
        font-weight: bold;
        padding: {SIZES['padding_normal']}px;
        border: none;
        font-size: {FONT_SIZES['small']};
    }}
"""

KP_DIALOG_STYLE = f"""
    QDialog {{
        background: {COLORS['white']};
    }}
"""


def apply_kp_info_frame_style(widget):
    """Применяет стиль для информационных блоков (серый фон, рамка)."""
    widget.setStyleSheet(KP_INFO_FRAME_STYLE)


def apply_kp_total_frame_style(widget):
    """Применяет стиль для блока итоговой суммы (синий фон)."""
    widget.setStyleSheet(KP_TOTAL_FRAME_STYLE)


def apply_kp_widget_theme(widget):
    """Применяет базовую тему ко всему виджету коммерческого предложения."""
    widget.setStyleSheet(KP_WIDGET_STYLE)


def apply_kp_dialog_style(widget):
    """Применяет базовый стиль диалога КП."""
    widget.setStyleSheet(KP_DIALOG_STYLE)

