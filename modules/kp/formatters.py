"""
Утилиты форматирования для модуля коммерческих предложений
"""

# Константа курса валют
EUR_TO_RUB_RATE = 100.0  # 1 EUR = 100 RUB


def format_price_with_spaces(price: float) -> str:
    """
    Форматирование цены с пробелами для разделения тысяч
    
    Args:
        price: Цена для форматирования
    
    Returns:
        Отформатированная строка цены (например: "3 433,00")
    """
    if price <= 0:
        return "-"
    
    # Разбиваем на целую и дробную части
    price_parts = f"{price:.2f}".split('.')
    integer_part = price_parts[0]
    decimal_part = price_parts[1] if len(price_parts) > 1 else "00"
    
    # Добавляем пробелы для разделения тысяч
    if len(integer_part) > 3:
        # Форматируем с пробелами каждые 3 цифры справа налево
        formatted_int = ''
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                formatted_int = ' ' + formatted_int
            formatted_int = digit + formatted_int
        integer_part = formatted_int
    
    return f"{integer_part},{decimal_part}"


def convert_price_to_rubles(price: float, manufacturer_name: str) -> float:
    """
    Конвертация цены в рубли
    
    Если производитель "Гидрозо", цена конвертируется из евро в рубли
    
    Args:
        price: Цена товара
        manufacturer_name: Название производителя
    
    Returns:
        Цена в рублях
    """
    if manufacturer_name and "гидрозо" in manufacturer_name.lower():
        return price * EUR_TO_RUB_RATE
    return price

