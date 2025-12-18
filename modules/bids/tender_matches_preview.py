"""
Модуль для создания превью совпадений в карточке закупки.
"""

from typing import Dict, Any, List, Optional
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget

from modules.styles.general_styles import (
    apply_label_style, apply_text_style_light, apply_frame_style, apply_font_weight
)


def get_score_color(score: float) -> tuple:
    """
    Возвращает цвет фона и текста в зависимости от score.
    
    Returns:
        (background_color, text_color) - кортеж из двух цветов
    """
    if score >= 100.0:
        return ("#d4edda", "#155724")  # Зеленый
    elif score >= 85.0:
        return ("#fff3cd", "#856404")  # Желтый
    elif score >= 56.0:
        return ("#cfe2ff", "#084298")  # Синий
    else:
        return ("#f8d7da", "#721c24")  # Красный


def create_matches_preview(
    summary: Optional[Dict[str, Any]],
    fetch_match_details_func
) -> Optional[QWidget]:
    """Создает небольшую секцию с найденными товарами из документов."""
    if not summary:
        return None
    
    container = QFrame()
    apply_frame_style(container, 'secondary')
    layout = QVBoxLayout(container)
    layout.setSpacing(6)
    layout.setContentsMargins(0, 0, 0, 0)
    
    title = QLabel("Совпадения по документам")
    apply_label_style(title, 'h3')
    apply_font_weight(title)
    layout.addWidget(title)
    
    stats_label = QLabel(
        f"100%: {summary.get('exact_count', 0)} • "
        f"85%: {summary.get('good_count', 0)} • "
        f"Всего: {summary.get('total_count', 0)}"
    )
    apply_label_style(stats_label, 'normal')
    apply_text_style_light(stats_label)
    layout.addWidget(stats_label)
    
    details = fetch_match_details_func(limit=3)
    if details:
        for detail in details:
            product_name = detail.get('product_name') or "Без названия"
            score = detail.get('score') or 0
            sheet = detail.get('sheet_name') or "лист"
            cell = detail.get('cell_address') or ""
            
            bg_color, text_color = get_score_color(score)
            item_label = QLabel(f"• {product_name} — {score:.0f}% ({sheet} {cell})")
            apply_label_style(item_label, 'normal')
            from modules.styles.general_styles import scale_size
            item_label.setStyleSheet(
                item_label.styleSheet() + 
                f"background-color: {bg_color}; "
                f"color: {text_color}; "
                f"padding: {scale_size(6)}px; "
                f"border-radius: {scale_size(4)}px;"
            )
            layout.addWidget(item_label)
    else:
        empty_label = QLabel("Документы обработаны, но совпадения не найдены.")
        apply_label_style(empty_label, 'normal')
        layout.addWidget(empty_label)
    
    return container
