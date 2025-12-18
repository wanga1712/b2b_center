"""Модуль для группировки совпадений по цветам."""

from typing import Any, Dict, List
from PyQt5.QtWidgets import QLabel, QVBoxLayout
from modules.styles.general_styles import apply_label_style, apply_text_color


def add_match_group(
    layout: QVBoxLayout,
    matches: List[Dict[str, Any]],
    title_emoji: str,
    title_text: str,
    text_color: str,
    create_card_func
):
    """Добавляет группу совпадений в layout"""
    if not matches:
        return
    title = QLabel(f"{title_emoji} {title_text} ({len(matches)})")
    apply_label_style(title, 'h3')
    apply_text_color(title, text_color)
    layout.addWidget(title)
    for detail in matches:
        layout.addWidget(create_card_func(detail))
    layout.addSpacing(12)

