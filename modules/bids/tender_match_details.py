"""Модуль для создания деталей совпадений в карточке закупки."""

from typing import Any, Dict, List, Optional
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from modules.styles.general_styles import (
    apply_label_style, apply_text_style_light, apply_text_color, apply_font_weight
)
from modules.styles.general_styles import apply_frame_style


def create_match_summary_block(match_summary: Optional[Dict[str, Any]]) -> QFrame:
    """Создание блока сводки по совпадениям."""
    frame = QFrame()
    layout = QVBoxLayout(frame)
    layout.setSpacing(6)
    
    title = QLabel("Результаты анализа документов")
    apply_label_style(title, 'h2')
    layout.addWidget(title)
    
    if not match_summary:
        empty_label = QLabel("Документы по закупке ещё не обработаны.")
        apply_label_style(empty_label, 'normal')
        apply_text_style_light(empty_label)
        layout.addWidget(empty_label)
        return frame
    
    summary_text = QLabel(
        f"100% совпадения: {match_summary.get('exact_count', 0)}\n"
        f"85%-100% совпадения: {match_summary.get('good_count', 0)}\n"
        f"56%-85% совпадения: {match_summary.get('brown_count', 0)}\n"
        f"Всего совпадений: {match_summary.get('total_count', 0)}"
    )
    apply_label_style(summary_text, 'normal')
    layout.addWidget(summary_text)
    return frame


def create_match_detail_card(detail: Dict[str, Any]) -> QWidget:
    """Создание карточки одного совпадения."""
    card = QFrame()
    layout = QVBoxLayout(card)
    layout.setSpacing(4)
    layout.setContentsMargins(8, 8, 8, 8)
    
    from modules.bids.tender_match_card_colors import get_match_card_colors
    product_name = detail.get('product_name') or "Без названия"
    score = detail.get('score') or 0
    border_color, bg_color, text_color = get_match_card_colors(score)
    
    card.setStyleSheet(
        f"QFrame {{"
        f"  border: 2px solid {border_color};"
        f"  background-color: {bg_color};"
        f"  border-radius: 6px;"
        f"  padding: 4px;"
        f"}}"
    )
    
    header = QLabel(f"{product_name} — {score:.0f}%")
    apply_label_style(header, 'normal')
    apply_font_weight(header)
    header.setStyleSheet(f"color: {text_color};")
    layout.addWidget(header)
    
    sheet = detail.get('sheet_name') or "лист"
    cell = detail.get('cell_address') or ""
    location = QLabel(f"{sheet} {cell}".strip())
    apply_label_style(location, 'small')
    location.setStyleSheet(f"color: {text_color};")
    layout.addWidget(location)
    
    source = detail.get('source_file')
    if source:
        source_label = QLabel(f"Файл: {source}")
        apply_label_style(source_label, 'small')
        source_label.setStyleSheet(f"color: {text_color};")
        layout.addWidget(source_label)
    
    snippet = detail.get("matched_display_text") or detail.get("matched_text")
    if snippet:
        snippet_label = QLabel(f"Фрагмент: {snippet}")
        snippet_label.setWordWrap(True)
        apply_label_style(snippet_label, "small")
        snippet_label.setStyleSheet(f"color: {text_color};")
        layout.addWidget(snippet_label)

    # Для Excel‑смет: показываем строку с заголовками столбцов и значениями
    row_data = detail.get("row_data") or {}
    full_row = row_data.get("full_row") or []
    if full_row:
        # Берём только ячейки с непустым значением и названием столбца
        excel_cells = []
        for cell_info in full_row:
            header = cell_info.get("column_name") or cell_info.get("column")
            value = cell_info.get("value")
            if not header or not value:
                continue
            excel_cells.append(f"{header}: {value}")
            if len(excel_cells) >= 6:
                break

        if excel_cells:
            excel_label = QLabel("Строка сметы:\n" + "\n".join(excel_cells))
            excel_label.setWordWrap(True)
            apply_label_style(excel_label, "small")
            excel_label.setStyleSheet(f"color: {text_color};")
            layout.addWidget(excel_label)
    
    return card


def create_match_details_block(details: List[Dict[str, Any]]) -> QFrame:
    """Создание блока с деталями совпадений."""
    frame = QFrame()
    layout = QVBoxLayout(frame)
    layout.setSpacing(8)
    
    title = QLabel("Найденные товары")
    apply_label_style(title, 'h2')
    layout.addWidget(title)
    
    if not details:
        empty_label = QLabel("Совпадения ещё не обнаружены.")
        apply_label_style(empty_label, 'normal')
        apply_text_style_light(empty_label)
        layout.addWidget(empty_label)
        return frame
    
    from modules.bids.tender_match_details_groups import add_match_group
    green_matches = [d for d in details if d.get('score', 0) >= 100.0]
    yellow_matches = [d for d in details if 85.0 <= d.get('score', 0) < 100.0]
    brown_matches = [d for d in details if 56.0 <= d.get('score', 0) < 85.0]
    
    add_match_group(layout, green_matches, "🟢", "100% совпадения", '#155724', create_match_detail_card)
    add_match_group(layout, yellow_matches, "🟡", "85%-100% совпадения", '#856404', create_match_detail_card)
    add_match_group(layout, brown_matches, "🟤", "56%-85% совпадения", '#5D2F0A', create_match_detail_card)
    
    return frame

