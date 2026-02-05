"""
MODULE: modules.bids.tender_status_badges
RESPONSIBILITY: Create status badges for tender cards.
ALLOWED: PyQt5, loguru, modules.styles.bids_styles.
FORBIDDEN: Database interaction.
ERRORS: None.

Модуль для создания значков статуса обработки закупок.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel

from loguru import logger

from modules.styles.bids_styles import apply_status_badge_style


def create_badge(text: str, text_color: str, background_color: str, tooltip: str) -> QLabel:
    """Создание значка статуса."""
    badge = QLabel(text)
    apply_status_badge_style(badge, text_color, background_color)
    badge.setToolTip(tooltip)
    return badge


def create_status_badges(
    summary: Optional[Dict[str, Any]],
    card_widget: QWidget,
) -> Optional[QWidget]:
    """
    Создание значков статуса обработки и совпадений.
    
    Args:
        summary: Сводка по совпадениям
        card_widget: Виджет карточки для установки стилей
        
    Returns:
        Виджет с значками статуса
    """
    tender_id = None
    if hasattr(card_widget, 'tender_data'):
        tender_id = card_widget.tender_data.get('id')
    
    if not tender_id:
        logger.warning("⚠️ [create_status_badges] tender_id отсутствует в данных закупки")
        return None
    
    container = QWidget()
    container_layout = QHBoxLayout(container)
    container_layout.setSpacing(8)
    container_layout.setContentsMargins(0, 0, 0, 0)
    
    if not summary:
        logger.info(f"🔴 [create_status_badges] Закупка {tender_id} не обработана - показываем красный значок")
        badge = create_badge("🔴 Не обработано", "#dc3545", "#fff3cd", "Документы не обработаны")
        container_layout.addWidget(badge)
        return container
    
    match_result = summary.get('match_result', {})
    error_reason = summary.get('error_reason')
    exact_count = summary.get('exact_count', 0)
    good_count = summary.get('good_count', 0)
    brown_count = summary.get('brown_count', 0)
    total_count = summary.get('total_count', 0) or match_result.get('match_count', 0)
    
    logger.info(f"📈 [create_status_badges] Статистика для закупки {tender_id}: "
               f"exact_count={exact_count}, good_count={good_count}, brown_count={brown_count}, total_count={total_count}")
    
    if error_reason:
        error_type = error_reason.split(":")[0] if ":" in error_reason else error_reason
        
        if error_type == "processing_error":
            error_text = f"🔵 Ошибка парсинга: {error_reason.split(':')[1][:30] if ':' in error_reason else error_reason[:30]}"
            badge_color = "#007bff"
            badge_bg = "#cfe2ff"
            card_border = "#007bff"
            card_bg = "#e7f3ff"
        else:
            error_text = {
                "no_documents": "❌ Нет документов",
                "no_workbook_files": "❌ Не удалось открыть файлы",
            }.get(error_type, f"❌ Ошибка: {error_reason[:30]}")
            badge_color = "#dc3545"
            badge_bg = "#f8d7da"
            card_border = "#dc3545"
            card_bg = "#fff5f5"
        
        badge = create_badge(error_text, badge_color, badge_bg, f"Ошибка обработки: {error_reason}")
        container_layout.addWidget(badge)
        
        # Безопасное добавление стилей к карточке
        try:
            current_style = card_widget.styleSheet() or ""
            # Если стиль многострочный (содержит фигурные скобки), добавляем стили внутри блока TenderCard
            if '{' in current_style and '}' in current_style:
                # Многострочный CSS - добавляем стили в конец блока TenderCard
                if 'TenderCard {' in current_style or 'TenderCard{' in current_style:
                    # Находим закрывающую скобку блока TenderCard
                    tender_card_end = current_style.find('TenderCard')
                    if tender_card_end >= 0:
                        # Ищем закрывающую скобку после TenderCard {
                        brace_start = current_style.find('{', tender_card_end)
                        if brace_start >= 0:
                            # Находим соответствующую закрывающую скобку
                            brace_count = 0
                            for i in range(brace_start, len(current_style)):
                                if current_style[i] == '{':
                                    brace_count += 1
                                elif current_style[i] == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        # Нашли закрывающую скобку блока TenderCard
                                        indent = '        '  # Стандартный отступ
                                        new_style = (
                                            current_style[:i] + 
                                            f"\n{indent}border: 3px solid {card_border};\n" +
                                            f"{indent}background-color: {card_bg};\n" +
                                            current_style[i:]
                                        )
                                        card_widget.setStyleSheet(new_style)
                                        return container
            # Если не удалось добавить в блок, добавляем в конец
            card_widget.setStyleSheet(
                f"{current_style.rstrip()}; "
                f"border: 3px solid {card_border}; "
                f"background-color: {card_bg}; "
                f"border-radius: 8px;"
            )
        except Exception as e:
            logger.debug(f"Ошибка при установке стиля карточки: {e}")
        
        return container
    
    if exact_count > 0:
        logger.info(f"🟢 [create_status_badges] Найдено {exact_count} совпадений 100% - показываем зеленый значок")
        badge = create_badge(
            f"🟢 {exact_count} (100%)",
            "#28a745",
            "#d4edda",
            f"100% совпадений. Найдено товаров: {exact_count}"
        )
        container_layout.addWidget(badge)
    
    if good_count > 0:
        logger.info(f"🟡 [create_status_badges] Найдено {good_count} совпадений 85%-100% - показываем желтый значок")
        badge = create_badge(
            f"🟡 {good_count} (85%-100%)",
            "#ffc107",
            "#fff3cd",
            f"85%-100% совпадений. Найдено товаров: {good_count}"
        )
        container_layout.addWidget(badge)
    
    if brown_count > 0:
        logger.info(f"🟤 [create_status_badges] Найдено {brown_count} совпадений 56%-85% - показываем коричневый значок")
        badge = create_badge(
            f"🟤 {brown_count} (56%-85%)",
            "#8B4513",
            "#F4E4C1",
            f"56%-85% совпадений. Найдено товаров: {brown_count}"
        )
        container_layout.addWidget(badge)
    
    if exact_count == 0 and good_count == 0 and brown_count == 0 and total_count == 0:
        logger.info(f"🔴 [create_status_badges] Совпадений не найдено - показываем красный значок")
        badge = create_badge(
            "🔴 0 совпадений",
            "#dc3545",
            "#f8d7da",
            "Совпадений не найдено"
        )
        container_layout.addWidget(badge)
    
    logger.info(f"✅ [create_status_badges] Карточка для закупки {tender_id} сформирована")
    return container

