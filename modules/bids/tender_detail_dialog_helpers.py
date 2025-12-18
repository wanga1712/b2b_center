"""Модуль с вспомогательными функциями для диалога деталей закупки."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from PyQt5.QtWidgets import QApplication

if TYPE_CHECKING:
    from services.tender_match_repository import TenderMatchRepository


def determine_registry_type(tender_data: Dict[str, Any]) -> str:
    """Определяет тип реестра (44ФЗ/223ФЗ)"""
    raw_value = (
        tender_data.get('registry_type')
        or tender_data.get('law')
        or ''
    )
    value = str(raw_value).lower()
    return '223fz' if '223' in value else '44fz'


def set_fullscreen_size(dialog):
    """Установка размера диалога в полный размер экрана"""
    screen = QApplication.primaryScreen()
    if screen:
        available_geometry = screen.availableGeometry()
        width = int(available_geometry.width() * 0.95)
        height = int(available_geometry.height() * 0.95)
        dialog.resize(width, height)
        x = available_geometry.x() + (available_geometry.width() - width) // 2
        y = available_geometry.y() + (available_geometry.height() - height) // 2
        dialog.move(x, y)
    else:
        from modules.styles.ui_config import configure_dialog
        configure_dialog(dialog, "Подробная информация о закупке", size_preset="tender_detail")


def load_match_data(
    tender_match_repository: Optional['TenderMatchRepository'],
    tender_id: Optional[int],
    registry_type: str,
    match_summary: Optional[Dict[str, Any]],
    match_details: Optional[List[Dict[str, Any]]]
) -> tuple:
    """Подгружает сводку и детали совпадений"""
    if not tender_match_repository or not tender_id:
        return match_summary or None, match_details or []
    
    if match_summary is None:
        match_summary = tender_match_repository.get_match_summary(tender_id, registry_type)
    
    if match_details is None:
        match_details = tender_match_repository.get_match_details(tender_id, registry_type, limit=20)
    
    return match_summary, match_details or []

