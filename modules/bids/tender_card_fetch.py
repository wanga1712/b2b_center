"""Модуль с методами получения данных для карточки закупки."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from services.tender_match_repository import TenderMatchRepository


def create_fetch_match_summary(
    tender_match_repository: Optional['TenderMatchRepository'],
    tender_id: Optional[int],
    registry_type: str,
    cache_ref
) -> Callable[[], Optional[Dict[str, Any]]]:
    """Создает функцию для получения сводки совпадений с кэшем"""
    def fetch():
        from modules.bids.tender_card_data_fetch import fetch_match_summary_with_cache
        cache_ref[0] = fetch_match_summary_with_cache(
            tender_match_repository, tender_id, registry_type, cache_ref[0]
        )
        return cache_ref[0]
    return fetch


def create_fetch_match_details(
    tender_match_repository: Optional['TenderMatchRepository'],
    tender_id: Optional[int],
    registry_type: str,
    cache_ref,
    cache_limit: int
) -> Callable[[Optional[int]], List[Dict[str, Any]]]:
    """Создает функцию для получения детальных совпадений с кэшем"""
    def fetch(limit: Optional[int] = None):
        from modules.bids.tender_card_data_fetch import fetch_match_details_with_cache
        if cache_ref[0] is None:
            summary_func = create_fetch_match_summary(
                tender_match_repository, tender_id, registry_type, [None]
            )
            if summary_func():
                cache_ref[0] = fetch_match_details_with_cache(
                    tender_match_repository, tender_id, registry_type,
                    None, cache_limit
                )
        return fetch_match_details_with_cache(
            tender_match_repository, tender_id, registry_type,
            cache_ref[0], cache_limit, limit
        )
    return fetch

