"""Модуль для форматирования данных в диалоге деталей закупки."""

from datetime import datetime
from typing import Any, Optional


def format_price(price: Optional[Any]) -> str:
    """Форматирование цены"""
    if not price:
        return "—"
    try:
        return f"{float(price):,.0f} ₽".replace(',', ' ')
    except:
        return str(price)


def format_date(date_value: Optional[Any]) -> str:
    """Форматирование даты"""
    if not date_value:
        return "—"
    try:
        if isinstance(date_value, str):
            date_value = datetime.strptime(date_value, '%Y-%m-%d').date()
        if hasattr(date_value, 'strftime'):
            return date_value.strftime('%d.%m.%Y')
        return str(date_value)
    except:
        return str(date_value) if date_value else "—"

