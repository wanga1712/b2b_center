"""
MODULE: modules.bids.tender_card_salesforce_styles
RESPONSIBILITY: CSS styles and color logic for Salesforce-like tender cards.
ALLOWED: typing, modules.styles.general_styles.
FORBIDDEN: Database interaction.
ERRORS: None.

Стили карточек закупок в стиле Salesforce CRM.
Карточки-лиды с цветовой индикацией приоритета и современным дизайном.
"""

from modules.styles.general_styles import COLORS, SIZES, FONT_SIZES
from typing import Dict, Any, Optional


def get_priority_color(tender_data: Dict[str, Any], match_summary: Optional[Dict[str, Any]]) -> str:
    """
    Определение цвета приоритета для закупки (как в Salesforce).
    
    Приоритет определяется по:
    - Проценту совпадения (match score)
    - Сумме закупки
    - Количеству совпадений
    
    Returns:
        Цвет для полоски слева: #28a745 (green), #ffc107 (amber), #007bff (blue), #6c757d (gray)
    """
    # Высокий приоритет: 100% совпадение и большая сумма
    if match_summary:
        exact_count = match_summary.get('exact_count', 0)
        total_count = match_summary.get('total_count', 0)
        
        # Если есть 100% совпадения
        if exact_count > 0:
            initial_price = tender_data.get('initial_price', 0)
            if initial_price and float(initial_price) >= 500000:  # >= 500k руб
                return "#28a745"  # Зеленый (high priority)
            return "#ffc107"  # Янтарный (medium-high)
        
        # Если есть хорошие совпадения (85%+)
        good_count = match_summary.get('good_count', 0)
        if good_count > 0:
            return "#007bff"  # Синий (medium)
        
        # Есть какие-то совпадения, но низкий процент
        if total_count > 0:
            return "#17a2b8"  # Голубой (low-medium)
    
    # Низкий приоритет или нет данных
    return "#6c757d"  # Серый (low)


def get_salesforce_card_style(priority_color: str) -> str:
    """
    Стиль карточки в стиле Salesforce с цветовой полоской слева.
    """
    return f"""
        TenderCard {{
            background: {COLORS['white']};
            border: 1px solid {COLORS['border']};
            border-left: 4px solid {priority_color};
            border-radius: {SIZES['border_radius_normal']}px;
            padding-left: 8px;
        }}
        TenderCard:hover {{
            border-left: 6px solid {priority_color};
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transform: translateY(-2px);
        }}
    """


def get_priority_badge_style(priority_color: str) -> Dict[str, str]:
    """
    Стиль бейджа приоритета.
    
    Returns:
        dict с ключами 'background', 'color', 'text'
    """
    priority_map = {
        "#28a745": {"background": "#d4edda", "color": "#155724", "text": "🔥 Высокий приоритет"},
        "#ffc107": {"background": "#fff3cd", "color": "#856404", "text": "⚡ Средний приоритет"},
        "#007bff": {"background": "#cfe2ff", "color": "#084298", "text": "📌 Нормальный"},
        "#17a2b8": {"background": "#d1ecf1", "color": "#0c5460", "text": "📎 Низкий"},
        "#6c757d": {"background": "#e2e3e5", "color": "#383d41", "text": "📋 Проверить"},
    }
    return priority_map.get(priority_color, priority_map["#6c757d"])


def get_convert_button_style() -> str:
    """Стиль кнопки конвертации в сделку (как в Salesforce)."""
    return f"""
        QPushButton {{
            background: {COLORS['success']};
            color: {COLORS['white']};
            border: none;
            border-radius: {SIZES['border_radius_small']}px;
            padding: {SIZES['padding_small']}px {SIZES['padding_normal']}px;
            font-weight: bold;
            font-size: {FONT_SIZES['normal']};
        }}
        QPushButton:hover {{
            background: #218838;
        }}
        QPushButton:pressed {{
            background: #1e7e34;
        }}
    """


def get_score_badge_style(score: float) -> Dict[str, str]:
    """
    Стиль бейджа процента совпадения.
    
    Args:
        score: Процент совпадения (0-100)
        
    Returns:
        dict с ключами 'background', 'color'
    """
    if score >= 100.0:
        return {"background": "#d4edda", "color": "#155724"}  # Зеленый
    elif score >= 85.0:
        return {"background": "#fff3cd", "color": "#856404"}  # Желтый
    elif score >= 56.0:
        return {"background": "#cfe2ff", "color": "#084298"}  # Синий
    else:
        return {"background": "#f8d7da", "color": "#721c24"}  # Красный

