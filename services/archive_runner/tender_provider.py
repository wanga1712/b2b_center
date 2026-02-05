"""
MODULE: services.archive_runner.tender_provider
RESPONSIBILITY: Provide tenders for processing, abstracting DB access and caching.
ALLOWED: TenderRepository, TenderCache, ProcessedTendersRepository, logging.
FORBIDDEN: Direct SQL queries (use repositories).
ERRORS: None.

Модуль для получения торгов и документов из базы данных.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from loguru import logger

from services.tender_services.tender_repository_facade import TenderRepositoryFacade
from services.archive_runner.tender_cache import TenderCache, CachedTender, AnalysisTenderCache
from services.archive_runner.processed_tenders_repository import ProcessedTendersRepository


class TenderProvider:
    """Предоставляет торги и документы для обработки."""

    def __init__(self, tender_repo: TenderRepositoryFacade, user_id: int, use_cache: bool = True):
        self.tender_repo = tender_repo
        self.user_id = user_id
        self.cache = TenderCache() if use_cache else None
        self.processed_repo = ProcessedTendersRepository(tender_repo.db_manager)

    def get_target_tenders(
        self,
        region_id: Optional[int] = None,
        limit: int = 1000,
        specific_tender_ids: Optional[List[Dict[str, Any]]] = None,
        registry_type: Optional[str] = None,
        tender_type: str = 'new',
    ) -> List[Dict[str, Any]]:
        """
        Возвращает список торгов (44ФЗ + 223ФЗ) согласно настройкам пользователя.
        
        Args:
            region_id: ID региона для фильтрации
            limit: Максимальное количество результатов
            specific_tender_ids: Список словарей с ключами 'id' и 'registry_type' для конкретных закупок
            registry_type: Тип реестра для фильтрации ('44fz' или '223fz'). Если None, возвращаются оба.
            tender_type: Тип торгов ('new' для новых, 'won' для разыгранных). По умолчанию 'new'.
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
            logger.warning(f"❌ У пользователя {self.user_id} нет настроенных ОКПД кодов. Настройте OKPD категории в разделе настроек.")
            return []

        # Формируем фильтры для кеша
        filters = {
            "okpd_codes": sorted(user_okpd_codes),
            "stop_words": sorted(user_stop_words),
            "region_id": region_id,
            "registry_type": registry_type,
            "tender_type": tender_type,
            "limit": limit,
        }
        
        # Пытаемся загрузить из кеша с защитой от ошибок
        cached_tenders = None
        if self.cache:
            try:
                cached_tenders = self.cache.load_tenders(self.user_id, filters)
            except Exception as cache_error:
                logger.warning(f"Ошибка при загрузке кеша торгов: {cache_error}", exc_info=True)
                cached_tenders = None
        
        if cached_tenders:
            # Кеш найден - проверяем статусы батч-запросом
            logger.info(f"Кеш найден: {len(cached_tenders)} закупок, проверяем статусы...")
            tender_ids_for_check = [(t.tender_id, t.registry_type) for t in cached_tenders]
            
            # Получаем актуальные статусы из БД (батч-запрос) с защитой
            try:
                status_updates = self._get_statuses_batch(tender_ids_for_check)
                logger.info(f"Получено обновлений статусов: {len(status_updates)} из {len(cached_tenders)} закупок")
            except Exception as status_error:
                logger.warning(f"Ошибка при получении статусов торгов: {status_error}", exc_info=True)
                status_updates = {}
            
            # Обновляем статусы в кешированных закупках и фильтруем по tender_type
            updated_tenders = []
            filtered_out_count = 0
            for cached_tender in cached_tenders:
                key = (cached_tender.tender_id, cached_tender.registry_type)
                old_status = cached_tender.status_id
                if key in status_updates:
                    cached_tender.status_id = status_updates[key]
                    if old_status != cached_tender.status_id:
                        logger.debug(f"Статус торга {cached_tender.tender_id} ({cached_tender.registry_type}) изменен: {old_status} -> {cached_tender.status_id}")
                
                # Фильтруем по tender_type
                if self._matches_tender_type(cached_tender, tender_type):
                    updated_tenders.append(cached_tender)
                else:
                    filtered_out_count += 1
                    logger.debug(f"Торг {cached_tender.tender_id} ({cached_tender.registry_type}) отфильтрован: status_id={cached_tender.status_id}, tender_type={tender_type}")
            
            # Преобразуем в формат для возврата
            tenders = self._cached_to_tenders(updated_tenders)
            
            logger.info(
                f"Использован кеш: {len(cached_tenders)} закупок в кеше, "
                f"после фильтрации по tender_type={tender_type}: {len(tenders)} закупок "
                f"(отфильтровано: {filtered_out_count})"
            )
            
            # Сохраняем обновленный кеш
            if self.cache:
                try:
                    self.cache.save_tenders(self.user_id, filters, tenders)
                except Exception as cache_save_error:
                    logger.warning(f"Ошибка при сохранении обновленного кеша: {cache_save_error}", exc_info=True)
            
            return tenders
        
        # Кеш не найден или отключен - получаем из БД
        logger.info("Кеш не найден или отключен, получаем закупки из БД...")
        tenders_44fz = []
        tenders_223fz = []
        
        # Получаем торги только указанного типа реестра, если указан
        if registry_type is None or registry_type == '44fz':
            if tender_type == 'won':
                tenders_44fz = self.tender_repo.get_won_tenders_44fz(
                    user_id=self.user_id,
                    user_okpd_codes=user_okpd_codes,
                    user_stop_words=user_stop_words,
                    region_id=region_id,
                    limit=limit,
                )
            else:
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
            if tender_type == 'won':
                tenders_223fz = self.tender_repo.get_won_tenders_223fz(
                    user_id=self.user_id,
                    user_okpd_codes=user_okpd_codes,
                    user_stop_words=user_stop_words,
                    region_id=region_id,
                    limit=limit,
                )
            else:
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

        # Фильтруем уже обработанные торги
        filtered_tenders = []
        skipped_count = 0

        # #region agent log
        import json
        import time
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        log_path = project_root / ".cursor" / "debug.log"

        try:
            with open(str(log_path), "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "filtering",
                    "hypothesisId": "FILTERING",
                    "location": "tender_provider.py:get_target_tenders:filtering_start",
                    "message": "Начинаем фильтрацию обработанных торгов",
                    "data": {
                        "total_tenders": len(all_tenders),
                        "tender_type": tender_type,
                        "registry_type": registry_type
                    },
                    "timestamp": int(time.time() * 1000)
                }, ensure_ascii=False) + "\n")
                f.flush()
        except Exception:
            pass
        # #endregion

        for tender in all_tenders:
            tender_id = tender.get("id")
            reg_type = tender.get("registry_type", registry_type or "44fz")

            # Проверяем по базовому имени папки (без суффикса типа торга)
            base_folder_name = f"{reg_type}_{tender_id}"

            # #region agent log
            is_processed = self.processed_repo.is_tender_processed(tender_id, reg_type, base_folder_name)
            try:
                with open(str(log_path), "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "filtering",
                        "hypothesisId": "FILTERING",
                        "location": "tender_provider.py:get_target_tenders:check_processed",
                        "message": "Проверка обработана ли торг",
                        "data": {
                            "tender_id": tender_id,
                            "reg_type": reg_type,
                            "base_folder_name": base_folder_name,
                            "is_processed": is_processed
                        },
                        "timestamp": int(time.time() * 1000)
                    }, ensure_ascii=False) + "\n")
                    f.flush()
            except Exception:
                pass
            # #endregion

            if is_processed:
                skipped_count += 1
                logger.debug(f"⏭️ Торг {tender_id} ({reg_type}) уже обработана, пропускаем")
            else:
                filtered_tenders.append(tender)

        logger.info(
            "Получено торгов: %s (44ФЗ: %s, 223ФЗ: %s)%s%s | Отфильтровано обработанных: %s",
            len(filtered_tenders),
            len([t for t in filtered_tenders if t.get("registry_type") == "44fz"]),
            len([t for t in filtered_tenders if t.get("registry_type") == "223fz"]),
            f" [фильтр: {registry_type}]" if registry_type else "",
            f" [тип: {tender_type}]" if tender_type != 'new' else "",
            skipped_count
        )

        # Сохраняем в кеш только не обработанные торги
        if self.cache and filtered_tenders:
            self.cache.save_tenders(self.user_id, filters, filtered_tenders)

        return filtered_tenders
    
    def _get_statuses_batch(self, tender_ids: List[Tuple[int, str]]) -> Dict[Tuple[int, str], Optional[int]]:
        """
        Получает статусы закупок батч-запросом.
        
        Args:
            tender_ids: Список кортежей (tender_id, registry_type)
            
        Returns:
            Словарь {(tender_id, registry_type): status_id}
        """
        if not tender_ids:
            return {}
        
        # Группируем по registry_type
        ids_by_registry: Dict[str, List[int]] = {}
        for tender_id, registry_type in tender_ids:
            if registry_type not in ids_by_registry:
                ids_by_registry[registry_type] = []
            ids_by_registry[registry_type].append(tender_id)
        
        status_map = {}
        
        # Получаем статусы для каждого реестра
        for reg_type, ids in ids_by_registry.items():
            try:
                # Используем метод репозитория для получения статусов
                # Получаем только необходимые поля (id, status_id) для оптимизации
                tenders = self.tender_repo.get_tenders_by_ids(
                    tender_ids_44fz=ids if reg_type == '44fz' else None,
                    tender_ids_223fz=ids if reg_type == '223fz' else None,
                )
                
                for tender in tenders:
                    key = (tender['id'], reg_type)
                    status_map[key] = tender.get('status_id')
            except Exception as e:
                logger.warning(f"Ошибка при получении статусов для {reg_type}: {e}")
        
        return status_map
    
    def _matches_tender_type(self, cached_tender: CachedTender, tender_type: str) -> bool:
        """
        Проверяет, соответствует ли кешированная закупка типу tender_type.
        
        Args:
            cached_tender: Кешированная закупка
            tender_type: Тип торгов ('new' или 'won')
        """
        if tender_type == 'new':
            # Новые: status_id = 1 (Новая) или status_id = 2 (Работа комиссии)
            return cached_tender.status_id in (1, 2)
        elif tender_type == 'won':
            # Разыгранные: status_id = 3 (Разыграна)
            return cached_tender.status_id == 3
        return True
    
    def _cached_to_tenders(self, cached_tenders: List[CachedTender]) -> List[Dict[str, Any]]:
        """Преобразует кешированные закупки в формат для возврата"""
        tenders = []
        for cached in cached_tenders:
            tender = {
                "id": cached.tender_id,
                "registry_type": cached.registry_type,
                "status_id": cached.status_id,
            }
            if cached.auction_name:
                tender["auction_name"] = cached.auction_name
            if cached.end_date:
                tender["end_date"] = cached.end_date
            if cached.delivery_end_date:
                tender["delivery_end_date"] = cached.delivery_end_date
            
            tenders.append(tender)
        
        return tenders

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

    def get_tenders_for_analysis(self, filters: Dict[str, Any], registry_type: str = "44fz",
                                tender_type: str = "won") -> List[Dict[str, Any]]:
        """
        Получает торги для анализа документов с использованием кэша анализа.

        Args:
            filters: Фильтры пользователя (okpd_codes, stop_words, region_id, category_id)
            registry_type: Тип реестра ("44fz" или "223fz")
            tender_type: Тип торгов ("new", "commission", "won")

        Returns:
            Список торгов для анализа
        """
        # Создаем кэш анализа
        analysis_cache = AnalysisTenderCache(db_manager=self.tender_repo.db_manager)

        # Пытаемся загрузить из кэша анализа
        cached_tenders = None
        if analysis_cache:
            try:
                cached_tenders = analysis_cache.load_tenders(self.user_id, filters)
                if cached_tenders:
                    logger.info(f"Найдено в кэше анализа: {len(cached_tenders)} торгов")
            except Exception as cache_error:
                logger.warning(f"Ошибка загрузки кэша анализа: {cache_error}", exc_info=True)
                cached_tenders = None

        if cached_tenders:
            # Фильтруем по типу торгов и преобразуем в формат для анализа
            filtered_tenders = []
            for cached in cached_tenders:
                if self._matches_tender_type(cached, tender_type):
                    tender = self._convert_cached_to_tender(cached)
                    filtered_tenders.append(tender)

            logger.info(f"После фильтрации по типу '{tender_type}': {len(filtered_tenders)} торгов")
            return filtered_tenders

        # Кэш не найден - получаем из TenderRepository
        logger.info("Кэш анализа не найден, получаем торги из БД...")

        if tender_type == "won":
            tenders = self.tender_repo.get_won_tenders_44fz(
                user_id=self.user_id,
                user_okpd_codes=filters.get("okpd_codes"),
                user_stop_words=filters.get("stop_words"),
                region_id=filters.get("region_id"),
                category_id=filters.get("category_id"),
                limit=10000  # Больший лимит для анализа
            ) if registry_type == "44fz" else self.tender_repo.get_won_tenders_223fz(
                user_id=self.user_id,
                user_okpd_codes=filters.get("okpd_codes"),
                user_stop_words=filters.get("stop_words"),
                region_id=filters.get("region_id"),
                category_id=filters.get("category_id"),
                limit=10000
            )
        elif tender_type == "commission":
            tenders = self.tender_repo.get_commission_tenders_44fz(
                user_id=self.user_id,
                user_okpd_codes=filters.get("okpd_codes"),
                user_stop_words=filters.get("stop_words"),
                region_id=filters.get("region_id"),
                category_id=filters.get("category_id"),
                limit=10000
            )
        else:  # new
            tenders = self.tender_repo.get_new_tenders_44fz(
                user_id=self.user_id,
                user_okpd_codes=filters.get("okpd_codes"),
                user_stop_words=filters.get("stop_words"),
                region_id=filters.get("region_id"),
                category_id=filters.get("category_id"),
                limit=10000
            ) if registry_type == "44fz" else self.tender_repo.get_new_tenders_223fz(
                user_id=self.user_id,
                user_okpd_codes=filters.get("okpd_codes"),
                user_stop_words=filters.get("stop_words"),
                region_id=filters.get("region_id"),
                category_id=filters.get("category_id"),
                limit=10000
            )

        logger.info(f"Получено из БД: {len(tenders) if tenders else 0} торгов для анализа")

        # Сохраняем в кэш анализа
        if analysis_cache and tenders:
            try:
                logger.info("Сохраняем торги в кэш анализа...")
                analysis_cache.save_tenders(self.user_id, filters, tenders)
                logger.info("Торги сохранены в кэш анализа")
            except Exception as cache_error:
                logger.warning(f"Ошибка сохранения в кэш анализа: {cache_error}", exc_info=True)

        return tenders or []

    def _matches_tender_type(self, cached_tender: CachedTender, tender_type: str) -> bool:
        """Проверяет, соответствует ли кешированная торг типу анализа"""
        if tender_type == 'new':
            return cached_tender.status_id in (1, 2)  # Новые или Работа комиссии
        elif tender_type == 'won':
            return cached_tender.status_id in (2, 3)  # Работа комиссии или Разыгранные
        elif tender_type == 'commission':
            return cached_tender.status_id == 2  # Только Работа комиссии
        return True

    def _convert_cached_to_tender(self, cached: CachedTender) -> Dict[str, Any]:
        """Преобразует CachedTender в формат торгов для анализа"""
        return {
            "id": cached.tender_id,
            "registry_type": cached.registry_type,
            "status_id": cached.status_id,
            "auction_name": cached.auction_name,
            "end_date": cached.end_date,
            "delivery_end_date": cached.delivery_end_date,
        }

