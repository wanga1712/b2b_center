"""
Модуль для обновления статуса карточки закупки.
"""

from typing import Optional
from PyQt5.QtWidgets import QWidget, QHBoxLayout


def update_status_widgets(
    card,
    status_container: Optional[QWidget],
    matches_preview: Optional[QWidget],
    create_status_badges_func,
    create_matches_preview_func
) -> tuple:
    """
    Обновляет виджеты статуса и превью совпадений в карточке.
    
    Args:
        card: Экземпляр карточки закупки
        status_container: Текущий контейнер статуса
        matches_preview: Текущий превью совпадений
        create_status_badges_func: Функция создания значков статуса
        create_matches_preview_func: Функция создания превью совпадений
        
    Returns:
        (new_status_container, new_matches_preview) - новые виджеты
    """
    # Удаляем старый контейнер статуса
    if status_container:
        if status_container.parent():
            parent_layout = status_container.parent().layout()
            if parent_layout:
                parent_layout.removeWidget(status_container)
        status_container.deleteLater()
    
    # Удаляем старое превью
    if matches_preview:
        layout = card.layout()
        if layout:
            layout.removeWidget(matches_preview)
        matches_preview.deleteLater()
    
    # Создаем новый контейнер статуса
    new_status_container = create_status_badges_func()
    if new_status_container:
        # Находим layout статуса и добавляем новый контейнер
        main_layout = card.layout()
        if main_layout:
            for i in range(main_layout.count()):
                item = main_layout.itemAt(i)
                if item and item.layout():
                    layout = item.layout()
                    # Проверяем, что это QHBoxLayout статуса (содержит stretch в конце)
                    if isinstance(layout, QHBoxLayout) and layout.count() > 0:
                        last_item = layout.itemAt(layout.count() - 1)
                        if last_item and last_item.spacerItem():
                            # Это layout статуса - вставляем новый контейнер в начало
                            layout.insertWidget(0, new_status_container)
                            break
    
    # Создаем новое превью
    new_matches_preview = create_matches_preview_func()
    if new_matches_preview:
        card.layout().addWidget(new_matches_preview)
    
    return new_status_container, new_matches_preview

