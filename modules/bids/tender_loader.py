"""
Модуль для загрузки данных о тендерах из репозитория.
"""

from typing import Optional
from loguru import logger
from PyQt5.QtWidgets import QMessageBox
import json
from pathlib import Path
from datetime import datetime

from modules.bids.tender_list_widget import TenderListWidget
from modules.bids.tender_loader_base import TenderLoaderBase
from modules.bids.search_params_cache import SearchParamsCache
from services.tender_repository import TenderRepository
from services.document_search_service import DocumentSearchService

# #region agent log
DEBUG_LOG_PATH = Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
# #endregion


class TenderLoader(TenderLoaderBase):
    """Класс для загрузки тендеров различных типов"""
    
    def __init__(
        self,
        tender_repo: TenderRepository,
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
        if not force and self.cache:
            cached_data = self.cache.get_tenders('44fz', 'new', user_id, filters)
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
            tenders, total_count = self._process_tenders_result(tenders)
            
            logger.info(f"Отображаем закупки 44ФЗ: {len(tenders)} (всего в БД: {total_count})")
            logger.info(f"Применены фильтры: категория={filters['category_id']}, регион={filters['region_id']}, стоп-слов={len(filters['user_stop_words'])}")
            
            # #region agent log
            try:
                tender_ids = [t.get('id') for t in tenders if t.get('id')]
                log_entry = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "E",
                    "location": f"{__file__}:88",
                    "message": "load_new_tenders_44fz: торги после SQL фильтрации",
                    "data": {
                        "tender_ids": tender_ids[:20],  # Первые 20 для логирования
                        "total_tenders_count": len(tenders),
                        "total_count_in_db": total_count,
                        "filters_applied": {
                            "category_id": filters.get('category_id'),
                            "region_id": filters.get('region_id'),
                            "stop_words_count": len(filters.get('user_stop_words', []))
                        }
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            except Exception as e:
                pass
            # #endregion
            
            # Сохраняем в кэш
            if self.cache:
                self.cache.save_tenders('44fz', 'new', user_id, filters, tenders, total_count)
            
            # Используем единый метод для загрузки и обновления
            # SQL уже отфильтровал неинтересные торги (is_interesting = FALSE)
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
        if not force and self.cache:
            cached_data = self.cache.get_tenders('223fz', 'new', user_id, filters)
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
            tenders = self.tender_repo.get_new_tenders_223fz(
                user_id=user_id,
                user_okpd_codes=filters['user_okpd_codes'],
                user_stop_words=filters['user_stop_words'],
                region_id=filters['region_id'],
                category_id=filters['category_id'],
                limit=1000
            )
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

