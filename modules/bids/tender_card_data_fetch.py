"""Модуль для получения данных совпадений для карточки закупки."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from services.tender_match_repository import TenderMatchRepository


def fetch_match_summary_with_cache(
    tender_match_repository: Optional['TenderMatchRepository'],
    tender_id: Optional[int],
    registry_type: str,
    cache: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Получение сводки совпадений с кэшем"""
    if not tender_match_repository or not tender_id:
        return None
    if cache is not None:
        return cache
    return tender_match_repository.get_match_summary(tender_id, registry_type)


def fetch_match_details_with_cache(
    tender_match_repository: Optional['TenderMatchRepository'],
    tender_id: Optional[int],
    registry_type: str,
    cache: Optional[List[Dict[str, Any]]],
    cache_limit: int,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Получение детальных совпадений с кэшем"""
    if not tender_match_repository or not tender_id:
        return []
    if cache is None:
        return tender_match_repository.get_match_details(tender_id, registry_type, limit=cache_limit)
    return cache[:limit] if limit else cache

