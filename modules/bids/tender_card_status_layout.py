"""Модуль для создания layout статуса в карточке закупки."""

from PyQt5.QtWidgets import QHBoxLayout


def create_status_layout(status_container, matches_preview):
    """Создает layout для статуса и превью совпадений"""
    status_layout = QHBoxLayout()
    status_layout.setSpacing(10)
    if status_container:
        status_layout.addWidget(status_container)
    status_layout.addStretch()
    return status_layout, matches_preview

