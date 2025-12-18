"""Модуль для создания статуса и превью совпадений в карточке закупки."""

from PyQt5.QtWidgets import QHBoxLayout


def add_status_and_preview(layout, create_status_func, create_preview_func):
    """Добавляет статус и превью совпадений в layout"""
    status_container = create_status_func()
    status_layout = QHBoxLayout()
    status_layout.setSpacing(10)
    if status_container:
        status_layout.addWidget(status_container)
    status_layout.addStretch()
    layout.addLayout(status_layout)
    
    matches_preview = create_preview_func()
    if matches_preview:
        layout.addWidget(matches_preview)
    
    return status_container, matches_preview

