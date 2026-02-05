"""
MODULE: modules.bids.tender_detail_dialog_helpers
RESPONSIBILITY: Helper functions for detail dialog (layout, data loading).
ALLOWED: PyQt5, typing, services.tender_match_repository.
FORBIDDEN: Heavy business logic.
ERRORS: None.

Модуль с вспомогательными функциями для диалога деталей закупки.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from PyQt5.QtWidgets import QApplication

if TYPE_CHECKING:
    from services.match_services.tender_match_repository_facade import TenderMatchRepositoryFacade as TenderMatchRepository


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
    """Подгружает сводку и детали совпадений из БД"""
    # #region agent log
    import json
    from datetime import datetime
    from pathlib import Path
    log_file = Path(r'c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log')
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            'timestamp': datetime.now().isoformat(),
            'location': 'tender_detail_dialog_helpers.py:load_match_data:entry',
            'message': 'Начало загрузки match data',
            'data': {
                'tender_id': tender_id,
                'registry_type': registry_type,
                'has_repository': tender_match_repository is not None,
                'match_summary_is_none': match_summary is None,
                'match_details_is_none': match_details is None
            },
            'hypothesisId': 'MATCH1',
            'sessionId': 'debug-session'
        }) + '\n')
    # #endregion agent log
    
    if not tender_match_repository or not tender_id:
        # #region agent log
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'location': 'tender_detail_dialog_helpers.py:load_match_data:no_repo_or_id',
                'message': 'Нет репозитория или tender_id',
                'data': {},
                'hypothesisId': 'MATCH2',
                'sessionId': 'debug-session'
            }) + '\n')
        # #endregion agent log
        return match_summary or None, match_details or []
    
    # Всегда загружаем актуальные данные из БД, игнорируя переданные initial значения
    match_summary = tender_match_repository.get_match_summary(tender_id, registry_type)
    # #region agent log
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            'timestamp': datetime.now().isoformat(),
            'location': 'tender_detail_dialog_helpers.py:load_match_data:after_summary',
            'message': 'После загрузки summary из БД',
            'data': {
                'summary': str(match_summary)[:200] if match_summary else 'None'
            },
            'hypothesisId': 'MATCH3',
            'sessionId': 'debug-session'
        }) + '\n')
    # #endregion agent log
    
    match_details = tender_match_repository.get_match_details(tender_id, registry_type, limit=20)
    # #region agent log
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            'timestamp': datetime.now().isoformat(),
            'location': 'tender_detail_dialog_helpers.py:load_match_data:after_details',
            'message': 'После загрузки details из БД',
            'data': {
                'details_count': len(match_details) if match_details else 0,
                'details_preview': str(match_details[:2]) if match_details else 'None'
            },
            'hypothesisId': 'MATCH4',
            'sessionId': 'debug-session'
        }) + '\n')
    # #endregion agent log
    
    return match_summary, match_details or []

