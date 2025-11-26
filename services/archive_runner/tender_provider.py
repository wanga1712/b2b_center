"""
Модуль для получения торгов и документов из базы данных.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from loguru import logger

from services.tender_repository import TenderRepository


class TenderProvider:
    """Предоставляет торги и документы для обработки."""

    def __init__(self, tender_repo: TenderRepository, user_id: int):
        self.tender_repo = tender_repo
        self.user_id = user_id

    def get_target_tenders(
        self,
        region_id: Optional[int] = None,
        limit: int = 1000,
        specific_tender_ids: Optional[List[Dict[str, Any]]] = None,
        registry_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Возвращает список торгов (44ФЗ + 223ФЗ) согласно настройкам пользователя.
        
        Args:
            region_id: ID региона для фильтрации
            limit: Максимальное количество результатов
            specific_tender_ids: Список словарей с ключами 'id' и 'registry_type' для конкретных закупок
            registry_type: Тип реестра для фильтрации ('44fz' или '223fz'). Если None, возвращаются оба.
        """
        # Если указаны конкретные ID закупок, возвращаем только их
        if specific_tender_ids:
            logger.info(f"Получение конкретных торгов: {len(specific_tender_ids)} закупок")
            
            # Разделяем закупки по типам реестра
            ids_44fz = [t['id'] for t in specific_tender_ids if t.get('registry_type') == '44fz']
            ids_223fz = [t['id'] for t in specific_tender_ids if t.get('registry_type') == '223fz']
            
            # Получаем закупки напрямую по ID
            tenders = self.tender_repo.get_tenders_by_ids(
                tender_ids_44fz=ids_44fz if ids_44fz else None,
                tender_ids_223fz=ids_223fz if ids_223fz else None,
            )
            
            logger.info(f"Получено конкретных торгов: {len(tenders)} (44ФЗ: {len(ids_44fz)}, 223ФЗ: {len(ids_223fz)})")
            return tenders
        
        # Иначе используем стандартную логику с настройками пользователя
        logger.info("Получение списка торгов для обработки (через TenderProvider)")
        user_okpd_list = self.tender_repo.get_user_okpd_codes(self.user_id)
        user_okpd_codes = [item.get("okpd_code") for item in user_okpd_list if item.get("okpd_code")]

        user_stop_words_list = self.tender_repo.get_user_stop_words(self.user_id)
        user_stop_words = [item.get("stop_word") for item in user_stop_words_list if item.get("stop_word")]

        if not user_okpd_codes:
            logger.warning(f"У пользователя {self.user_id} нет настроенных ОКПД кодов")
            return []

        tenders_44fz = []
        tenders_223fz = []
        
        # Получаем торги только указанного типа реестра, если указан
        if registry_type is None or registry_type == '44fz':
            tenders_44fz = self.tender_repo.get_new_tenders_44fz(
                user_id=self.user_id,
                user_okpd_codes=user_okpd_codes,
                user_stop_words=user_stop_words,
                region_id=region_id,
                limit=limit,
            )
            for tender in tenders_44fz:
                tender["registry_type"] = "44fz"
        
        if registry_type is None or registry_type == '223fz':
            tenders_223fz = self.tender_repo.get_new_tenders_223fz(
                user_id=self.user_id,
                user_okpd_codes=user_okpd_codes,
                user_stop_words=user_stop_words,
                region_id=region_id,
                limit=limit,
            )
            for tender in tenders_223fz:
                tender["registry_type"] = "223fz"

        all_tenders = tenders_44fz + tenders_223fz
        logger.info(
            "Получено торгов: %s (44ФЗ: %s, 223ФЗ: %s)%s",
            len(all_tenders),
            len(tenders_44fz),
            len(tenders_223fz),
            f" [фильтр: {registry_type}]" if registry_type else "",
        )
        return all_tenders

    def get_tender_documents(self, tender_id: int, registry_type: str) -> List[Dict[str, Any]]:
        """
        Возвращает список документов торга по ID и типу реестра.
        """
        documents = self.tender_repo.get_tender_documents(tender_id, registry_type)
        if not documents:
            logger.warning(
                "Для торга %s (%s) не найдено документов",
                tender_id,
                registry_type,
            )
        return documents

