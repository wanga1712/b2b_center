"""
Бизнес-логика для модуля коммерческих предложений

Содержит функции для:
- Расчет количества упаковки при вводе веса
- Обработка данных товаров
- Расчет итоговых сумм с учетом скидок
- Расчет рабочих дней
- Распределение стоимости доставки
"""

import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger


def calculate_packaging_quantity(
    requested_weight: float,
    unit_weight: float
) -> int:
    """
    Расчет количества единиц упаковки при вводе веса товара
    
    Если пользователь вводит вес (например, 255 кг), а товар продается
    мешками по 20 кг, функция рассчитывает необходимое количество мешков
    с округлением вверх.
    
    Args:
        requested_weight: Запрашиваемый вес товара (кг)
        unit_weight: Вес одной единицы упаковки (кг)
    
    Returns:
        Количество единиц упаковки (округлено вверх)
    
    Examples:
        >>> calculate_packaging_quantity(255, 20)
        13  # 255 / 20 = 12.75, округляем вверх до 13
        
        >>> calculate_packaging_quantity(100, 25)
        4  # 100 / 25 = 4.0, результат 4
    """
    if unit_weight <= 0:
        logger.warning(f"Некорректный вес единицы упаковки: {unit_weight}")
        return 0
    
    if requested_weight <= 0:
        return 0
    
    # Округление вверх с помощью math.ceil
    quantity = math.ceil(requested_weight / unit_weight)
    logger.debug(
        f"Расчет упаковки: {requested_weight} кг / {unit_weight} кг = {quantity} ед."
    )
    return quantity


def calculate_item_total(
    price: float,
    quantity: int,
    discount_percent: float = 0.0
) -> float:
    """
    Расчет итоговой суммы по позиции с учетом скидки
    
    Args:
        price: Цена за единицу
        quantity: Количество единиц
        discount_percent: Процент скидки (0-100)
    
    Returns:
        Итоговая сумма по позиции
    """
    if price < 0 or quantity < 0:
        return 0.0
    
    if discount_percent < 0:
        discount_percent = 0.0
    elif discount_percent > 100:
        discount_percent = 100.0
    
    subtotal = price * quantity
    discount_amount = subtotal * (discount_percent / 100)
    total = subtotal - discount_amount
    
    return round(total, 2)


def calculate_quotation_total(items: list) -> float:
    """
    Расчет итоговой суммы коммерческого предложения
    
    Args:
        items: Список позиций, каждая содержит 'total' (итоговая сумма)
    
    Returns:
        Общая сумма коммерческого предложения
    """
    total = sum(item.get('total', 0.0) for item in items)
    return round(total, 2)


def format_price(price: float) -> str:
    """
    Форматирование цены для отображения
    
    Args:
        price: Цена
    
    Returns:
        Отформатированная строка цены
    """
    return f"{price:,.2f}".replace(',', ' ')


def parse_weight_input(weight_str: str) -> Optional[float]:
    """
    Парсинг введенного веса из строки
    
    Args:
        weight_str: Строка с весом (может содержать "кг", пробелы и т.д.)
    
    Returns:
        Вес в килограммах или None при ошибке
    """
    try:
        # Удаляем все нечисловые символы кроме точки и запятой
        cleaned = weight_str.strip().lower()
        cleaned = cleaned.replace('кг', '').replace('kg', '').strip()
        cleaned = cleaned.replace(',', '.')
        
        weight = float(cleaned)
        return weight if weight > 0 else None
    except (ValueError, AttributeError):
        logger.warning(f"Не удалось распарсить вес: {weight_str}")
        return None


def get_unit_display_name(container_type: str, size: str) -> str:
    """
    Формирование названия единицы измерения для отображения
    
    Убирает тире из единиц измерения (например, "ведро - 20л" -> "ведро 20л")
    
    Args:
        container_type: Тип тары (мешок, бочка и т.д.)
        size: Размер упаковки
    
    Returns:
        Строка для отображения единицы измерения без тире
    """
    container_type = container_type.strip() if container_type else ""
    size = size.strip() if size else ""
    
    if container_type and size:
        # Убираем тире, если есть
        result = f"{container_type} {size}".replace(' - ', ' ').replace('- ', '').strip()
        return result
    elif container_type:
        return container_type.replace(' - ', ' ').replace('- ', '').strip()
    elif size:
        return size.replace(' - ', ' ').replace('- ', '').strip()
    else:
        return "шт"


def calculate_working_days(start_date: datetime, days: int) -> datetime:
    """
    Расчет даты через указанное количество рабочих дней
    
    Исключает выходные дни (суббота, воскресенье)
    
    Args:
        start_date: Начальная дата
        days: Количество рабочих дней
    
    Returns:
        Дата через указанное количество рабочих дней
    """
    current_date = start_date
    working_days_added = 0
    
    while working_days_added < days:
        current_date += timedelta(days=1)
        # Пропускаем выходные (суббота=5, воскресенье=6)
        if current_date.weekday() < 5:  # 0-4 это понедельник-пятница
            working_days_added += 1
    
    return current_date


def format_date_for_display(date: datetime) -> str:
    """
    Форматирование даты для отображения
    
    Args:
        date: Дата для форматирования
    
    Returns:
        Отформатированная строка даты (например: "12.11.2025")
    """
    return date.strftime("%d.%m.%Y")


def distribute_delivery_cost(delivery_cost: float, items_count: int) -> float:
    """
    Распределение стоимости доставки равными долями между позициями
    
    Args:
        delivery_cost: Общая стоимость доставки
        items_count: Количество позиций в корзине
    
    Returns:
        Стоимость доставки на одну позицию
    """
    if items_count <= 0:
        return 0.0
    return round(delivery_cost / items_count, 2)
