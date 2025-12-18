"""
Модуль для обновления статуса карточки закупки.
"""

from PyQt5.QtWidgets import QHBoxLayout


def update_card_status(
    card,
    create_status_badges_func,
    create_matches_preview_func
):
    """Обновление статуса карточки без пересоздания."""
    card._match_summary_cache = None
    card._match_details_cache = None
    
    # Удаляем старый контейнер статуса
    if hasattr(card, 'status_container') and card.status_container:
        if card.status_container.parent():
            parent_layout = card.status_container.parent().layout()
            if parent_layout:
                parent_layout.removeWidget(card.status_container)
        card.status_container.deleteLater()
        card.status_container = None
    
    # Удаляем старый превью совпадений
    if hasattr(card, 'matches_preview') and card.matches_preview:
        layout = card.layout()
        if layout:
            layout.removeWidget(card.matches_preview)
        card.matches_preview.deleteLater()
        card.matches_preview = None
    
    # Создаем новый контейнер статуса
    card.status_container = create_status_badges_func()
    if card.status_container:
        main_layout = card.layout()
        for i in range(main_layout.count()):
            item = main_layout.itemAt(i)
            if item and item.layout():
                layout = item.layout()
                if isinstance(layout, QHBoxLayout) and layout.count() > 0:
                    last_item = layout.itemAt(layout.count() - 1)
                    if last_item and last_item.spacerItem():
                        layout.insertWidget(0, card.status_container)
                        break
    
    # Создаем новый превью совпадений
    card.matches_preview = create_matches_preview_func()
    if card.matches_preview:
        card.layout().addWidget(card.matches_preview)

