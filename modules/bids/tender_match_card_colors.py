"""Модуль для определения цветов карточек совпадений по score."""

def get_match_card_colors(score: float) -> tuple:
    """
    Возвращает цвета для карточки совпадения в зависимости от score.
    
    Returns:
        (border_color, bg_color, text_color) - кортеж из трех цветов
    """
    if score >= 100.0:
        return ("#28a745", "#d4edda", "#155724")
    elif score >= 85.0:
        return ("#ffc107", "#fff3cd", "#856404")
    elif score >= 56.0:
        return ("#8B4513", "#F4E4C1", "#5D2F0A")
    else:
        return ("#6c757d", "#e9ecef", "#495057")

