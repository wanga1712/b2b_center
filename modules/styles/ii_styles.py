"""
Стили для модуля искусственного интеллекта (чат).
"""

from modules.styles.general_styles import COLORS, FONT_SIZES, SIZES

USER_MESSAGE_STYLE = f"""
    QFrame {{
        background: {COLORS['primary']};
        border-radius: {SIZES['border_radius_xlarge']}px;
        padding: {SIZES['padding_large']}px {SIZES['padding_large'] * 2}px;
        margin: {SIZES['padding_large']}px 0px;
        max-width: 80%;
    }}
"""

ASSISTANT_MESSAGE_STYLE = f"""
    QFrame {{
        background: #E3F2FD;
        border-radius: {SIZES['border_radius_xlarge']}px;
        padding: {SIZES['padding_large']}px {SIZES['padding_large'] * 2}px;
        margin: {SIZES['padding_large']}px 0px;
        max-width: 80%;
    }}
"""

INPUT_PANEL_STYLE = f"""
    QFrame {{
        background: {COLORS['white']};
        border-top: 1px solid {COLORS['border']};
    }}
"""


def apply_chat_message_style(widget, is_user: bool):
    """Применяет стиль к сообщению чата в зависимости от отправителя."""
    widget.setStyleSheet(USER_MESSAGE_STYLE if is_user else ASSISTANT_MESSAGE_STYLE)


def apply_chat_input_panel_style(widget):
    """Применяет стиль к панели ввода сообщений."""
    widget.setStyleSheet(INPUT_PANEL_STYLE)

