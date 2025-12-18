"""
Утилиты для работы с карточками закупок.
"""

from typing import Any, Dict, Optional
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt

from modules.styles.general_styles import apply_label_style


def build_link_label(text: str, url: str) -> QLabel:
    """Создает кликабельную текстовую ссылку."""
    link_label = QLabel(f'<a href="{url}">{text}</a>')
    apply_label_style(link_label, 'small')
    link_label.setTextFormat(Qt.RichText)
    link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
    link_label.setOpenExternalLinks(True)
    return link_label


def format_balance_holder(data: Dict[str, Any]) -> Optional[str]:
    """Форматирует подпись балансодержателя."""
    name = data.get('balance_holder_name')
    inn = data.get('balance_holder_inn')
    if name and inn:
        return f"{name} (ИНН {inn})"
    return name or None

