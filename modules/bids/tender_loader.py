"""
MODULE: modules.bids.tender_loader
RESPONSIBILITY: Load tender data from repositories and update UI widgets.
ALLOWED: typing, loguru, PyQt5.QtWidgets, modules.bids.tender_list_widget, modules.bids.tender_loader_base, modules.bids.search_params_cache, services.tender_repository, services.document_search_service.
FORBIDDEN: Direct SQL queries (use TenderRepository).
ERRORS: None (handles exceptions).

Модуль для загрузки данных о тендерах из репозитория.
"""

from typing import Optional
from loguru import logger
from PyQt5.QtWidgets import QMessageBox

from modules.bids.tender_list_widget import TenderListWidget
from modules.bids.tender_loader_base import TenderLoaderBase
from modules.bids.search_params_cache import SearchParamsCache
from services.tender_services.tender_repository_facade import TenderRepositoryFacade
from services.document_search_service import DocumentSearchService

class TenderLoader(TenderLoaderBase):
    """Класс для загрузки тендеров различных типов"""
    
    def __init__(
        self,
        tender_repo: TenderRepositoryFacade,
        document_search_service: Optional[DocumentSearchService] = None,
        cache: Optional[SearchParamsCache] = None,
    ):
        """
        Инициализация загрузчика тендеров
        
        Args:
            tender_repo: Репозиторий для работы с тендерами
            document_search_service: Сервис поиска документов (опционально)
            cache: Кэш для закупок (опционально)
        """
        super().__init__(tender_repo)
        self.document_search_service = document_search_service
        self.cache = cache
    
    def load_new_tenders_44fz(
        self,
        widget: TenderListWidget,
        user_id: int,
        category_filter_combo=None,
        force: bool = False,
        parent_widget=None
    ):
        """Загрузка новых закупок 44ФЗ"""
        if not self.tender_repo:
            logger.warning("Репозиторий закупок не инициализирован")
            return
        
        widget.show_loading()
        filters = self._get_user_filters(user_id, category_filter_combo, self.cache)
        
        # Проверяем кэш (только если не принудительное обновление)
        cached_data = None
        # #region agent log
        import json
        import time
        log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "I",
                    "location": "tender_loader.py:load_tenders_44fz:check_cache",
                    "message": "Проверка кэша для 44ФЗ",
                    "data": {
                        "force": force,
                        "has_cache": self.cache is not None,
                        "user_id": user_id,
                        "filters": filters
                    },
                    "timestamp": int(time.time() * 1000)
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        if not force and self.cache:
            cached_data = self.cache.get_tenders('44fz', 'new', user_id, filters)
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "I",
                        "location": "tender_loader.py:load_tenders_44fz:cache_result",
                        "message": "Результат проверки кэша для 44ФЗ",
                        "data": {
                            "cached_data_exists": cached_data is not None,
                            "cached_count": len(cached_data['tenders']) if cached_data else 0
                        },
                        "timestamp": int(time.time() * 1000)
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            if cached_data:
                logger.info(f"Используем кэш: {len(cached_data['tenders'])} закупок 44ФЗ (новые)")
                widget.set_tenders(cached_data['tenders'], cached_data.get('total_count'))
                widget.hide_loading()
                if self.document_search_service:
                    self.document_search_service.ensure_products_loaded()
                return
        
        # Проверяем, выбрана ли категория
        if not filters['user_okpd_codes']:
            logger.warning("Категория не выбрана - закупки не будут загружены")
            widget.hide_loading()
            widget.set_tenders([], 0)  # Очищаем виджет
            if parent_widget:
                QMessageBox.information(
                    parent_widget, 
                    "Выберите категорию", 
                    "Для загрузки закупок необходимо выбрать категорию ОКПД в настройках.\n\n"
                    "Перейдите на вкладку 'Настройки' и выберите категорию из списка."
                )
            return
        
        try:
            tenders = self.tender_repo.get_new_tenders_44fz(
                user_id=user_id,
                user_okpd_codes=filters['user_okpd_codes'],
                user_stop_words=filters['user_stop_words'],
                region_id=filters['region_id'],
                category_id=filters['category_id'],
                limit=1000
            )
            # #region agent log
            import json
            import time
            log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "G",
                        "location": "tender_loader.py:load_tenders_44fz:after_fetch",
                        "message": "Получены закупки из репозитория (после SQL фильтрации)",
                        "data": {
                            "count_before_process": len(tenders) if tenders else 0,
                            "user_id": user_id,
                            "region_id": filters['region_id'],
                            "category_id": filters['category_id']
                        },
                        "timestamp": int(time.time() * 1000)
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            tenders, total_count = self._process_tenders_result(tenders)
            
            logger.info(f"Отображаем закупки 44ФЗ: {len(tenders)} (всего в БД: {total_count})")
            logger.info(f"Применены фильтры: категория={filters['category_id']}, регион={filters['region_id']}, стоп-слов={len(filters['user_stop_words'])}")
            
            # Сохраняем в кэш
            if self.cache:
                self.cache.save_tenders('44fz', 'new', user_id, filters, tenders, total_count)
            
            # Используем единый метод для загрузки и обновления
            # SQL уже отфильтровал неинтересные торги (is_interesting = FALSE)
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "G",
                        "location": "tender_loader.py:load_tenders_44fz:before_set_tenders",
                        "message": "Передача закупок в виджет",
                        "data": {
                            "count": len(tenders) if tenders else 0,
                            "total_count": total_count
                        },
                        "timestamp": int(time.time() * 1000)
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            widget.set_tenders(tenders, total_count)
            
            if self.document_search_service:
                self.document_search_service.ensure_products_loaded()
        except Exception as e:
            logger.error(f"Ошибка при загрузке закупок 44ФЗ: {e}")
            widget.hide_loading()
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", f"Не удалось загрузить закупки:\n{e}")
    
    def load_new_tenders_223fz(
        self,
        widget: TenderListWidget,
        user_id: int,
        category_filter_combo=None,
        force: bool = False,
        parent_widget=None
    ):
        """Загрузка новых закупок 223ФЗ"""
        if not self.tender_repo:
            logger.warning("Репозиторий закупок не инициализирован")
            return
        
        widget.show_loading()
        filters = self._get_user_filters(user_id, category_filter_combo, self.cache)
        
        # Проверяем кэш (только если не принудительное обновление)
        cached_data = None
        # #region agent log
        import json
        import time
        log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "I",
                    "location": "tender_loader.py:load_tenders_223fz:check_cache",
                    "message": "Проверка кэша для 223ФЗ",
                    "data": {
                        "force": force,
                        "has_cache": self.cache is not None,
                        "user_id": user_id,
                        "filters": filters
                    },
                    "timestamp": int(time.time() * 1000)
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        if not force and self.cache:
            cached_data = self.cache.get_tenders('223fz', 'new', user_id, filters)
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "I",
                        "location": "tender_loader.py:load_tenders_223fz:cache_result",
                        "message": "Результат проверки кэша для 223ФЗ",
                        "data": {
                            "cached_data_exists": cached_data is not None,
                            "cached_count": len(cached_data['tenders']) if cached_data else 0
                        },
                        "timestamp": int(time.time() * 1000)
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            if cached_data:
                logger.info(f"Используем кэш: {len(cached_data['tenders'])} закупок 223ФЗ (новые)")
                widget.set_tenders(cached_data['tenders'], cached_data.get('total_count'))
                widget.hide_loading()
                if self.document_search_service:
                    self.document_search_service.ensure_products_loaded()
                return
        
        # Проверяем, выбрана ли категория
        if not filters['user_okpd_codes']:
            logger.warning("Категория не выбрана - закупки не будут загружены")
            widget.hide_loading()
            widget.set_tenders([], 0)  # Очищаем виджет
            if parent_widget:
                QMessageBox.information(
                    parent_widget, 
                    "Выберите категорию", 
                    "Для загрузки закупок необходимо выбрать категорию ОКПД в настройках.\n\n"
                    "Перейдите на вкладку 'Настройки' и выберите категорию из списка."
                )
            return
        
        try:
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "J",
                        "location": "tender_loader.py:load_tenders_223fz:before_fetch",
                        "message": "Перед запросом 223ФЗ из БД",
                        "data": {
                            "user_id": user_id,
                            "okpd_codes_count": len(filters['user_okpd_codes']) if filters['user_okpd_codes'] else 0,
                            "stop_words_count": len(filters['user_stop_words']) if filters['user_stop_words'] else 0,
                            "region_id": filters['region_id'],
                            "category_id": filters['category_id']
                        },
                        "timestamp": int(time.time() * 1000)
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            tenders = self.tender_repo.get_new_tenders_223fz(
                user_id=user_id,
                user_okpd_codes=filters['user_okpd_codes'],
                user_stop_words=filters['user_stop_words'],
                region_id=filters['region_id'],
                category_id=filters['category_id'],
                limit=1000
            )
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "J",
                        "location": "tender_loader.py:load_tenders_223fz:after_fetch",
                        "message": "После запроса 223ФЗ из БД",
                        "data": {
                            "tenders_count": len(tenders) if tenders else 0
                        },
                        "timestamp": int(time.time() * 1000)
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            tenders, total_count = self._process_tenders_result(tenders)
            
            logger.info(f"Отображаем закупки 223ФЗ: {len(tenders)} (всего в БД: {total_count})")
            logger.info(f"Применены фильтры: категория={filters['category_id']}, регион={filters['region_id']}, стоп-слов={len(filters['user_stop_words'])}")
            
            # Сохраняем в кэш
            if self.cache:
                self.cache.save_tenders('223fz', 'new', user_id, filters, tenders, total_count)
            
            # Используем единый метод для загрузки и обновления
            widget.set_tenders(tenders, total_count)
            
            if self.document_search_service:
                self.document_search_service.ensure_products_loaded()
        except Exception as e:
            logger.error(f"Ошибка при загрузке закупок 223ФЗ: {e}")
            widget.hide_loading()
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", f"Не удалось загрузить закупки:\n{e}")
    
    def load_won_tenders_44fz(
        self,
        widget: TenderListWidget,
        user_id: int,
        category_filter_combo=None,
        force: bool = False,
        parent_widget=None
    ):
        """Загрузка разыгранных закупок 44ФЗ"""
        if not self.tender_repo:
            logger.warning("Репозиторий закупок не инициализирован")
            return
        
        widget.show_loading()
        filters = self._get_user_filters(user_id, category_filter_combo, self.cache)
        
        # Проверяем, выбрана ли категория
        if not filters['user_okpd_codes']:
            logger.warning("Категория не выбрана - закупки не будут загружены")
            widget.hide_loading()
            widget.set_tenders([], 0)
            if parent_widget:
                QMessageBox.information(
                    parent_widget, 
                    "Выберите категорию", 
                    "Для загрузки закупок необходимо выбрать категорию ОКПД в настройках.\n\n"
                    "Перейдите на вкладку 'Настройки' и выберите категорию из списка."
                )
            return
        
        # Проверяем кэш (только если не принудительное обновление)
        cached_data = None
        if not force and self.cache:
            cached_data = self.cache.get_tenders('44fz', 'won', user_id, filters)
            if cached_data:
                logger.info(f"Используем кэш: {len(cached_data['tenders'])} закупок 44ФЗ (разыгранные)")
                widget.set_tenders(cached_data['tenders'], cached_data.get('total_count'))
                widget.hide_loading()
                if self.document_search_service:
                    self.document_search_service.ensure_products_loaded()
                return
        
        try:
            tenders = self.tender_repo.get_won_tenders_44fz(
                user_id=user_id,
                user_okpd_codes=filters['user_okpd_codes'],
                user_stop_words=filters['user_stop_words'],
                region_id=filters['region_id'],
                category_id=filters['category_id'],
                limit=1000
            )
            tenders, total_count = self._process_tenders_result(tenders)
            
            logger.info(f"Отображаем разыгранные закупки 44ФЗ: {len(tenders)} (всего в БД: {total_count})")
            logger.info(f"Применены фильтры: категория={filters['category_id']}, регион={filters['region_id']}, стоп-слов={len(filters['user_stop_words'])}")
            
            # Сохраняем в кэш
            if self.cache:
                self.cache.save_tenders('44fz', 'won', user_id, filters, tenders, total_count)
            
            # Используем единый метод для загрузки и обновления
            widget.set_tenders(tenders, total_count)
            
            if self.document_search_service:
                self.document_search_service.ensure_products_loaded()
        except Exception as e:
            logger.error(f"Ошибка при загрузке разыгранных закупок 44ФЗ: {e}")
            widget.hide_loading()
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", f"Не удалось загрузить закупки:\n{e}")
    
    def load_won_tenders_223fz(
        self,
        widget: TenderListWidget,
        user_id: int,
        category_filter_combo=None,
        force: bool = False,
        parent_widget=None
    ):
        """Загрузка разыгранных закупок 223ФЗ"""
        if not self.tender_repo:
            logger.warning("Репозиторий закупок не инициализирован")
            return
        
        widget.show_loading()
        filters = self._get_user_filters(user_id, category_filter_combo, self.cache)
        
        # Проверяем, выбрана ли категория
        if not filters['user_okpd_codes']:
            logger.warning("Категория не выбрана - закупки не будут загружены")
            widget.hide_loading()
            widget.set_tenders([], 0)
            if parent_widget:
                QMessageBox.information(
                    parent_widget, 
                    "Выберите категорию", 
                    "Для загрузки закупок необходимо выбрать категорию ОКПД в настройках.\n\n"
                    "Перейдите на вкладку 'Настройки' и выберите категорию из списка."
                )
            return
        
        # Проверяем кэш (только если не принудительное обновление)
        cached_data = None
        if not force and self.cache:
            cached_data = self.cache.get_tenders('223fz', 'won', user_id, filters)
            if cached_data:
                logger.info(f"Используем кэш: {len(cached_data['tenders'])} закупок 223ФЗ (разыгранные)")
                widget.set_tenders(cached_data['tenders'], cached_data.get('total_count'))
                widget.hide_loading()
                if self.document_search_service:
                    self.document_search_service.ensure_products_loaded()
                return
        
        try:
            tenders = self.tender_repo.get_won_tenders_223fz(
                user_id=user_id,
                user_okpd_codes=filters['user_okpd_codes'],
                user_stop_words=filters['user_stop_words'],
                region_id=filters['region_id'],
                category_id=filters['category_id'],
                limit=1000
            )
            tenders, total_count = self._process_tenders_result(tenders)
            
            logger.info(f"Отображаем разыгранные закупки 223ФЗ: {len(tenders)} (всего в БД: {total_count})")
            logger.info(f"Применены фильтры: категория={filters['category_id']}, регион={filters['region_id']}, стоп-слов={len(filters['user_stop_words'])}")
            
            # Сохраняем в кэш
            if self.cache:
                self.cache.save_tenders('223fz', 'won', user_id, filters, tenders, total_count)
            
            # Используем единый метод для загрузки и обновления
            widget.set_tenders(tenders, total_count)
            
            if self.document_search_service:
                self.document_search_service.ensure_products_loaded()
        except Exception as e:
            logger.error(f"Ошибка при загрузке разыгранных закупок 223ФЗ: {e}")
            widget.hide_loading()
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", f"Не удалось загрузить закупки:\n{e}")
    
    def load_commission_tenders_44fz(
        self,
        widget: TenderListWidget,
        user_id: int,
        category_filter_combo=None,
        force: bool = False,
        parent_widget=None
    ):
        """Загрузка закупок 44ФЗ со статусом 'Работа комиссии' (status_id = 2)"""
        if not self.tender_repo:
            logger.warning("Репозиторий закупок не инициализирован")
            return
        
        widget.show_loading()
        filters = self._get_user_filters(user_id, category_filter_combo, self.cache)
        
        # Проверяем, выбрана ли категория
        if not filters['user_okpd_codes']:
            logger.warning("Категория не выбрана - закупки не будут загружены")
            widget.hide_loading()
            widget.set_tenders([], 0)
            if parent_widget:
                QMessageBox.information(
                    parent_widget, 
                    "Выберите категорию", 
                    "Для загрузки закупок необходимо выбрать категорию ОКПД в настройках.\n\n"
                    "Перейдите на вкладку 'Настройки' и выберите категорию из списка."
                )
            return
        
        # Проверяем кэш (только если не принудительное обновление)
        cached_data = None
        if not force and self.cache:
            cached_data = self.cache.get_tenders('44fz', 'commission', user_id, filters)
            if cached_data:
                logger.info(f"Используем кэш: {len(cached_data['tenders'])} закупок 44ФЗ (работа комиссии)")
                widget.set_tenders(cached_data['tenders'], cached_data.get('total_count'))
                widget.hide_loading()
                if self.document_search_service:
                    self.document_search_service.ensure_products_loaded()
                return
        
        try:
            tenders = self.tender_repo.get_commission_tenders_44fz(
                user_id=user_id,
                user_okpd_codes=filters['user_okpd_codes'],
                user_stop_words=filters['user_stop_words'],
                region_id=filters['region_id'],
                category_id=filters['category_id'],
                limit=1000
            )
            tenders, total_count = self._process_tenders_result(tenders)
            
            logger.info(f"Отображаем закупки 44ФЗ (работа комиссии): {len(tenders)} (всего в БД: {total_count})")
            logger.info(f"Применены фильтры: категория={filters['category_id']}, регион={filters['region_id']}, стоп-слов={len(filters['user_stop_words'])}")
            
            # Сохраняем в кэш
            if self.cache:
                self.cache.save_tenders('44fz', 'commission', user_id, filters, tenders, total_count)
            
            widget.set_tenders(tenders, total_count)
            
            if self.document_search_service:
                self.document_search_service.ensure_products_loaded()
        except Exception as e:
            logger.error(f"Ошибка при загрузке закупок 44ФЗ (работа комиссии): {e}")
            widget.hide_loading()
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", f"Не удалось загрузить закупки:\n{e}")

