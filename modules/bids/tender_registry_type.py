"""
MODULE: modules.bids.tender_registry_type
RESPONSIBILITY: Determine registry type (44FZ/223FZ) from tender data.
ALLOWED: typing.
FORBIDDEN: External dependencies.
ERRORS: None.

Модуль для определения типа реестра закупки.
"""

from typing import Dict, Any


def determine_registry_type(tender_data: Dict[str, Any]) -> str:
    """Определяет тип реестра (44ФЗ/223ФЗ) для именования папок"""
    raw_value = (
        tender_data.get('registry_type')
        or tender_data.get('law')
        or ''
    )
    value = str(raw_value).lower()
    return '223fz' if '223' in value else '44fz'

