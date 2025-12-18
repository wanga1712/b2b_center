"""
Специализированные стили для модулей заявок (bids).
"""

from modules.styles.general_styles import COLORS, SIZES, FONT_SIZES


TENDER_CARD_STYLE = f"""
    TenderCard {{
        background: {COLORS['white']};
        border: 1px solid {COLORS['border']};
        border-radius: {SIZES['border_radius_normal']}px;
        min-height: {SIZES['table_row_height'] * 3}px;
    }}
    TenderCard:hover {{
        border: 2px solid {COLORS['primary']};
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }}
"""

CHECKBOX_STYLE = f"""
    QCheckBox {{
        spacing: {SIZES['padding_normal']}px;
    }}
    QCheckBox::indicator {{
        width: {int(SIZES['button_height'] * 1.3)}px;
        height: {int(SIZES['button_height'] * 1.3)}px;
        border: 2px solid {COLORS['border']};
        border-radius: {int(SIZES['button_height'] * 1.3) // 2}px;
        background: {COLORS['white']};
    }}
    QCheckBox::indicator:checked {{
        background: {COLORS['primary']};
        border: 2px solid {COLORS['primary']};
    }}
    QCheckBox::indicator:checked::after {{
        content: "★";
        color: {COLORS['white']};
        font-size: {FONT_SIZES['large']};
    }}
"""

def get_badge_template() -> str:
    """(Устар.) Шаблон больше не используется напрямую."""
    return ""

BID_CARD_STYLE = f"""
    QFrame {{
        background: {COLORS['white']};
        border: 1px solid {COLORS['border']};
        border-radius: {SIZES['border_radius_normal']}px;
        min-height: {SIZES['table_row_height'] * 2}px;
    }}
    QFrame:hover {{
        border: 2px solid {COLORS['primary']};
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }}
"""


def apply_tender_card_style(widget):
    widget.setStyleSheet(TENDER_CARD_STYLE)


def apply_tender_checkbox_style(widget):
    widget.setStyleSheet(CHECKBOX_STYLE)


def apply_status_badge_style(widget, text_color, background_color):
    """Применяет стиль бейджа без format() — напрямую через f-строку."""
    widget.setStyleSheet(
        f"""
        QLabel {{
            color: {text_color};
            font-weight: bold;
            font-size: {FONT_SIZES['normal']};
            padding: {SIZES['padding_small']}px {SIZES['padding_normal']}px;
            background: {background_color};
            border-radius: {SIZES['border_radius_small']}px;
        }}
        """
    )


def apply_bid_card_style(widget):
    widget.setStyleSheet(BID_CARD_STYLE)

KANBAN_HEADER_STYLE = f"""
    QLabel {{
        background: {COLORS['primary']};
        color: {COLORS['white']};
        padding: {SIZES['padding_normal']}px;
        border-radius: {SIZES['border_radius_small']}px;
        font-weight: bold;
    }}
"""

KANBAN_COLUMN_STYLE = f"""
    QFrame {{
        background: {COLORS['white']};
        border: 1px solid {COLORS['border']};
        border-radius: {SIZES['border_radius_normal']}px;
    }}
"""


def apply_kanban_header_style(widget):
    widget.setStyleSheet(KANBAN_HEADER_STYLE)


def apply_kanban_column_style(widget):
    widget.setStyleSheet(KANBAN_COLUMN_STYLE)

