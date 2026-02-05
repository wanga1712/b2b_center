"""
MODULE: modules.bids.tender_card_data
RESPONSIBILITY: Data fetching and caching for tender cards.
ALLOWED: typing, services.tender_match_repository.
FORBIDDEN: Direct SQL queries.
ERRORS: None.

Модуль для работы с данными карточки закупки (кэширование и получение).
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from services.match_services.tender_match_repository_facade import TenderMatchRepositoryFacade as TenderMatchRepository


def fetch_match_summary(
    tender_match_repository: Optional['TenderMatchRepository'],
    tender_id: Optional[int],
    registry_type: str,
    cache: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Получение сводки совпадений с кэшем."""
    if tender_match_repository is None or tender_id is None:
        return None
    if cache is None:
        return tender_match_repository.get_match_summary(tender_id, registry_type)
    return cache


def fetch_match_details(
    tender_match_repository: Optional['TenderMatchRepository'],
    tender_id: Optional[int],
    registry_type: str,
    cache: Optional[List[Dict[str, Any]]],
    cache_limit: int = 20,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Получение детальных совпадений с кэшем."""
    if tender_match_repository is None or tender_id is None:
        return []
    if cache is None:
        return tender_match_repository.get_match_details(
            tender_id, registry_type, limit=cache_limit
        )
    details = cache or []
    if limit:
        return details[:limit]
    return details

