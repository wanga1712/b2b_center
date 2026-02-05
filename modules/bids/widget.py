"""
MODULE: modules.bids.widget
RESPONSIBILITY: Main container widget for Bids module (44-FZ/223-FZ).
ALLOWED: PyQt5, typing, loguru, modules.bids.*, services.*, core.tender_database.
FORBIDDEN: Direct SQL execution (delegate to specialized managers).
ERRORS: None.

Виджет для управления закупками (44ФЗ и 223ФЗ)

Виджет предоставляет интерфейс для:
- Управления новыми закупками 44ФЗ и 223ФЗ через канбан-доски
- Просмотра разыгранных закупок
- Настройки параметров закупок
- Отслеживания закупок в работе
"""

from PyQt5.QtWidgets import QWidget
from typing import Optional
from pathlib import Path
from loguru import logger


# Импортируем модули для обработки процессов и загрузки тендеров
from modules.bids.tender_loader import TenderLoader
from modules.bids.document_processor import DocumentProcessor
from modules.bids.search_params_cache import SearchParamsCache

# Импортируем новые модули для рефакторинга
from modules.bids.bids_tender_loader import BidsTenderLoader
from modules.bids.bids_document_analyzer import BidsDocumentAnalyzer
from modules.bids.bids_cache_manager import BidsCacheManager
from modules.bids.bids_database_manager import BidsDatabaseManager
from modules.bids.bids_tabs_manager import BidsTabsManager
from modules.bids.bids_ui_builder import BidsUIBuilder

# Импортируем репозиторий для работы с закупками
from services.tender_services.tender_repository_facade import TenderRepositoryFacade
from services.match_services.tender_match_repository_facade import TenderMatchRepositoryFacade
from services.document_search_service import DocumentSearchService
from core.tender_database import TenderDatabaseManager
from config.settings import config
from core.database import DatabaseManager
from psycopg2.extras import RealDictCursor

# DOCUMENT_DOWNLOAD_DIR - путь к директории для скачивания документов из ЕИС
# Настраивается через переменную окружения DOCUMENT_DOWNLOAD_DIR в .env файле
# Пример: DOCUMENT_DOWNLOAD_DIR=C:\Projects\Documents\Tenders


class BidsWidget(QWidget):
    """
    Виджет для управления закупками
    
    Содержит вкладки для различных типов закупок и их статусов.
    """
    
    def __init__(
        self,
        product_db_manager: Optional[DatabaseManager] = None,
        tender_repository: Optional[TenderRepositoryFacade] = None,
        tender_match_repository: Optional[TenderMatchRepositoryFacade] = None,
        document_search_service: Optional[DocumentSearchService] = None,
    ):
        """
        Инициализация виджета закупок
        
        Args:
            product_db_manager: Менеджер БД продуктов (для обратной совместимости)
            tender_repository: Репозиторий закупок (опционально, создается через DI если не передан)
            tender_match_repository: Репозиторий результатов поиска (опционально)
            document_search_service: Сервис поиска документов (опционально)
        """
        super().__init__()
        
        # Внедрение зависимостей через DI контейнер или переданные параметры
        from core.dependency_injection import container
        
        # Инициализация подключения к БД tender_monitor (обязательно)
        if not config.tender_database:
            error_msg = "Конфигурация БД tender_monitor не задана. Проверьте переменные окружения в .env файле."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Используем переданные зависимости или создаем через контейнер
            if tender_repository:
                self.tender_repo = tender_repository
                self.tender_db_manager = tender_repository.db_manager if hasattr(tender_repository, 'db_manager') else None
            else:
                self.tender_db_manager = container.get_tender_database_manager()
                self.tender_repo = container.get_tender_repository()
            
            if tender_match_repository:
                self.tender_match_repo = tender_match_repository
            else:
                self.tender_match_repo = container.get_tender_match_repository()
            # Алиас для обратной совместимости с новым именем атрибута
            self.tender_match_repository = self.tender_match_repo
            
            logger.info("Подключение к БД tender_monitor установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к БД tender_monitor: {e}")
            raise  # Пробрасываем ошибку, так как подключение обязательно
        
        # Временный ID пользователя (позже будет из системы авторизации)
        self.current_user_id = 1
        self.product_db_manager = product_db_manager
        
        # Инициализация сервиса поиска документов
        if document_search_service:
            self.document_search_service = document_search_service
        elif self.product_db_manager:
            # Получаем путь к директории для скачивания документов из .env
            download_dir = Path(config.document_download_dir) if config.document_download_dir else Path.home() / "Downloads" / "ЕИС_Документация"
            self.document_search_service = DocumentSearchService(
                self.product_db_manager,
                download_dir,
                unrar_path=config.unrar_tool,
                winrar_path=config.winrar_path,
            )
            logger.info("Сервис поиска по документации инициализирован")
        else:
            # Пытаемся получить через контейнер
            try:
                self.document_search_service = container.get_document_search_service()
                logger.info("Сервис поиска по документации получен через DI контейнер")
            except Exception as e:
                logger.warning(f"Сервис поиска документации недоступен: {e}")
                self.document_search_service = None
        
        # Инициализируем кэш параметров поиска (до загрузчика тендеров, т.к. он его использует)
        self.search_params_cache = SearchParamsCache()
        
        # Инициализируем загрузчик тендеров
        tender_loader_base = TenderLoader(
            tender_repo=self.tender_repo,
            document_search_service=self.document_search_service,
            cache=self.search_params_cache
        )
        self.tender_loader = BidsTenderLoader(tender_loader_base)
        
        # Инициализируем процессор документов
        document_processor_base = DocumentProcessor(user_id=self.current_user_id)
        self.document_analyzer = BidsDocumentAnalyzer(document_processor_base)
        
        # Инициализируем менеджеры
        self.cache_manager = BidsCacheManager(self.search_params_cache)
        self.db_manager = BidsDatabaseManager(
            self.tender_db_manager,
            self.tender_repo,
            self.tender_match_repo,
            self.current_user_id,
            self.search_params_cache
        )
        
        # Создаем UI с Dashboard (Windows 11 + Salesforce style)
        ui_builder = BidsUIBuilder(
            parent_widget=self,
            tender_repo=self.tender_repo,
            user_id=self.current_user_id,
            search_params_cache=self.search_params_cache,
            document_search_service=self.document_search_service,
            tender_match_repo=self.tender_match_repo,
            tender_match_repository=self.tender_match_repo
        )
        
        # Получаем все компоненты UI из builder
        (
            self.analyze_button, self.analyze_all_button, self.refresh_button,
            self.stack_widget, self.dashboard, self.settings_tab,
            self.tenders_44fz_widget, self.tenders_223fz_widget,
            self.won_tenders_44fz_widget, self.won_tenders_223fz_widget,
            self.commission_tenders_44fz_widget, back_button, tabs_widget
        ) = ui_builder.build_ui()
        
        # Подключаем обработчики кнопок действий
        self.analyze_button.clicked.connect(self.handle_analyze_selected_tenders)
        self.analyze_all_button.clicked.connect(self.handle_analyze_all_tenders)
        self.refresh_button.clicked.connect(self.refresh_current_feed)
        
        # Подключаем навигацию Dashboard
        self.dashboard.section_selected.connect(self._on_dashboard_section_selected)
        self.dashboard.settings_clicked.connect(lambda: self.stack_widget.setCurrentIndex(2))  # settings
        back_button.clicked.connect(self._on_back_to_dashboard)  # dashboard
        
        # Подключаем переключение вкладок для отображения разделов
        tabs_widget.currentChanged.connect(self._on_tab_changed)
        
        # Текущий активный виджет
        self.current_widget = None
        self.current_section_id = None
        self.current_section_title = None
        
        # Подключаем обработчики изменения выбора закупок
        for widget in [
            self.tenders_44fz_widget, self.tenders_223fz_widget,
            self.won_tenders_44fz_widget, self.won_tenders_223fz_widget,
            self.commission_tenders_44fz_widget
        ]:
            if hasattr(widget, 'selection_changed'):
                widget.selection_changed.connect(self.on_tender_selection_changed)
        
        # Инициализируем менеджер загрузки
        self.tender_loader_manager = BidsTenderLoader(self.tender_loader.tender_loader)
        
        # Сохраняем ссылку на tabs для навигации
        self._tabs_widget = tabs_widget
        
        # По умолчанию показываем Dashboard (index 0)
        if hasattr(self, 'stack_widget'):
            self.stack_widget.setCurrentIndex(0)  # 0 = Dashboard
        
        # Автозагрузка закупок, если настройки были сохранены ранее
        self._autoload_tenders_if_settings_saved()
        
        # Обновляем счетчики на Dashboard, если настройки были сохранены
        self._update_dashboard_counts_if_settings_saved()
    
    def _update_dashboard_counts_if_settings_saved(self):
        """Обновление счетчиков на Dashboard, если настройки были сохранены"""
        try:
            if not hasattr(self, 'search_params_cache') or not self.search_params_cache:
                return
            
            if not self.search_params_cache.is_settings_saved():
                logger.debug("Настройки не сохранены, счетчики не обновляются")
                return
            
            # Получаем параметры из кэша
            region_id = self.search_params_cache.get_region_id()
            category_id = self.search_params_cache.get_category_id()
            user_okpd_codes = None  # Получим из репозитория
            user_stop_words = None  # Получим из репозитория
            
            # Получаем ОКПД коды пользователя
            if self.tender_repo:
                try:
                    okpd_list = self.tender_repo.get_user_okpd_codes(self.current_user_id, category_id)
                    user_okpd_codes = [item.get('okpd_code') for item in okpd_list if item.get('okpd_code')]
                except Exception as e:
                    logger.warning(f"Не удалось получить ОКПД коды пользователя: {e}")
            
            # Получаем стоп-слова пользователя
            if self.tender_repo:
                try:
                    stop_words_list = self.tender_repo.get_user_stop_words(self.current_user_id)
                    user_stop_words = [item.get('stop_word') for item in stop_words_list if item.get('stop_word')]
                except Exception as e:
                    logger.warning(f"Не удалось получить стоп-слова пользователя: {e}")
            
            # Обновляем счетчики для каждого раздела
            section_counts = {}
            
            try:
                # Новые 44ФЗ - используем limit=1 чтобы быстро получить количество
                # Но лучше использовать отдельный метод для подсчета, если он есть
                # #region agent log
                import json
                import time
                log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "A",
                            "location": "modules/bids/widget.py:_update_dashboard_counts_if_settings_saved:before_get_new_tenders_44fz",
                            "message": "Параметры запроса новых закупок 44ФЗ",
                            "data": {
                                "user_id": self.current_user_id,
                                "user_okpd_codes_count": len(user_okpd_codes) if user_okpd_codes else 0,
                                "user_stop_words_count": len(user_stop_words) if user_stop_words else 0,
                                "region_id": region_id,
                                "category_id": category_id,
                                "limit": 1000
                            },
                            "timestamp": int(time.time() * 1000)
                        }, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
                
                tenders = self.tender_repo.get_new_tenders_44fz(
                    user_id=self.current_user_id,
                    user_okpd_codes=user_okpd_codes,
                    user_stop_words=user_stop_words,
                    region_id=region_id,
                    category_id=category_id,
                    limit=1000  # Получаем все для точного подсчета (можно оптимизировать позже)
                )
                
                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "A",
                            "location": "modules/bids/widget.py:_update_dashboard_counts_if_settings_saved:after_get_new_tenders_44fz",
                            "message": "Результат запроса новых закупок 44ФЗ",
                            "data": {
                                "tenders_count": len(tenders) if tenders else 0,
                                "tenders_is_none": tenders is None,
                                "tenders_is_empty": tenders == [] if tenders is not None else None
                            },
                            "timestamp": int(time.time() * 1000)
                        }, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
                
                section_counts['purchases_44fz_new'] = len(tenders) if tenders else 0
                
                # #region agent log - проверка количества торгов с is_interesting = FALSE
                try:
                    if self.tender_db_manager:
                        # Проверка количества исключенных торгов
                        check_query = """
                            SELECT COUNT(DISTINCT r.id) as excluded_count
                            FROM reestr_contract_44_fz r
                            WHERE r.status_id = 1
                            AND EXISTS (
                                SELECT 1 FROM tender_document_matches tdm_filter
                                WHERE tdm_filter.tender_id = r.id 
                                AND tdm_filter.registry_type = '44fz'
                                AND tdm_filter.is_interesting = FALSE
                            )
                        """
                        excluded_result = self.tender_db_manager.execute_query(check_query, None, RealDictCursor)
                        excluded_count = excluded_result[0].get('excluded_count', 0) if excluded_result else 0
                        
                        # Детальная проверка: когда и почему они были помечены как неинтересные
                        detail_query = """
                            SELECT
                                tdm.tender_id,
                                tdm.match_count,
                                tdm.match_percentage,
                                tdm.is_interesting,
                                tdm.error_reason,
                                tdm.processed_at,
                                tdm.processing_time_seconds
                            FROM tender_document_matches tdm
                            INNER JOIN reestr_contract_44_fz r ON r.id = tdm.tender_id
                            WHERE r.status_id = 1
                            AND tdm.registry_type = '44fz'
                            AND tdm.is_interesting = FALSE
                            ORDER BY tdm.processed_at DESC
                            LIMIT 20
                        """
                        detail_result = self.tender_db_manager.execute_query(detail_query, None, RealDictCursor)
                        excluded_details = [dict(row) for row in detail_result] if detail_result else []
                        # Преобразуем Decimal и дату в сериализуемый вид
                        def _normalize(value):
                            from decimal import Decimal
                            if isinstance(value, Decimal):
                                return float(value)
                            return value
                        excluded_details_safe = []
                        for item in excluded_details[:5]:
                            excluded_details_safe.append({k: _normalize(v) for k, v in item.items()})
                        
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "F",
                                "location": "modules/bids/widget.py:_update_dashboard_counts_if_settings_saved:check_excluded",
                                "message": "Проверка количества торгов с is_interesting = FALSE",
                                "data": {
                                    "excluded_count": excluded_count,
                                    "returned_count": len(tenders) if tenders else 0,
                                    "excluded_details_sample": excluded_details_safe  # Первые 5 для анализа
                                },
                                "timestamp": int(time.time() * 1000)
                            }, ensure_ascii=False) + "\n")
                except Exception as check_error:
                    # #region agent log
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "F",
                                "location": "modules/bids/widget.py:_update_dashboard_counts_if_settings_saved:check_excluded_error",
                                "message": "Ошибка при проверке исключенных торгов",
                                "data": {
                                    "error": str(check_error)
                                },
                                "timestamp": int(time.time() * 1000)
                            }, ensure_ascii=False) + "\n")
                    except Exception:
                        pass
                    # #endregion
                # #endregion
                
            except Exception as e:
                logger.warning(f"Ошибка при получении количества новых закупок 44ФЗ: {e}")
                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "A",
                            "location": "modules/bids/widget.py:_update_dashboard_counts_if_settings_saved:error_get_new_tenders_44fz",
                            "message": "Ошибка при получении новых закупок 44ФЗ",
                            "data": {
                                "error": str(e)
                            },
                            "timestamp": int(time.time() * 1000)
                        }, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
                section_counts['purchases_44fz_new'] = 0
            
            try:
                # Новые 223ФЗ
                tenders = self.tender_repo.get_new_tenders_223fz(
                    user_id=self.current_user_id,
                    user_okpd_codes=user_okpd_codes,
                    user_stop_words=user_stop_words,
                    region_id=region_id,
                    category_id=category_id,
                    limit=1000
                )
                section_counts['purchases_223fz_new'] = len(tenders) if tenders else 0
            except Exception as e:
                logger.warning(f"Ошибка при получении количества новых закупок 223ФЗ: {e}")
                section_counts['purchases_223fz_new'] = 0
            
            try:
                # Разыгранные 44ФЗ
                tenders = self.tender_repo.get_won_tenders_44fz(
                    user_id=self.current_user_id,
                    user_okpd_codes=user_okpd_codes,
                    user_stop_words=user_stop_words,
                    region_id=region_id,
                    category_id=category_id,
                    limit=1000
                )
                section_counts['purchases_44fz_won'] = len(tenders) if tenders else 0
            except Exception as e:
                logger.warning(f"Ошибка при получении количества разыгранных закупок 44ФЗ: {e}")
                section_counts['purchases_44fz_won'] = 0
            
            try:
                # Разыгранные 223ФЗ
                tenders = self.tender_repo.get_won_tenders_223fz(
                    user_id=self.current_user_id,
                    user_okpd_codes=user_okpd_codes,
                    user_stop_words=user_stop_words,
                    region_id=region_id,
                    category_id=category_id,
                    limit=1000
                )
                section_counts['purchases_223fz_won'] = len(tenders) if tenders else 0
            except Exception as e:
                logger.warning(f"Ошибка при получении количества разыгранных закупок 223ФЗ: {e}")
                section_counts['purchases_223fz_won'] = 0
            
            try:
                # Работа комиссии 44ФЗ
                tenders = self.tender_repo.get_commission_tenders_44fz(
                    user_id=self.current_user_id,
                    user_okpd_codes=user_okpd_codes,
                    user_stop_words=user_stop_words,
                    region_id=region_id,
                    category_id=category_id,
                    limit=1000
                )
                section_counts['purchases_44fz_commission'] = len(tenders) if tenders else 0
            except Exception as e:
                logger.warning(f"Ошибка при получении количества закупок 'Работа комиссии' 44ФЗ: {e}")
                section_counts['purchases_44fz_commission'] = 0
            
            # Обновляем статистику фильтрации на Dashboard
            if hasattr(self, 'dashboard') and self.dashboard and hasattr(self.dashboard, 'update_filtering_stats'):
                try:
                    # Получаем статистику фильтрации для 44fz
                    # OKPD: торги до фильтра OKPD
                    okpd_total = 0
                    okpd_filtered = 0

                    # Стоп-слова: торги до фильтра стоп-слов
                    stop_words_total = 0
                    stop_words_filtered = 0

                    if user_okpd_codes and category_id:
                        # Получаем все торги с OKPD из категории (до фильтра стоп-слов)
                        try:
                            all_with_okpd = self.tender_repo.get_new_tenders_44fz(
                                user_id=self.current_user_id,
                                user_okpd_codes=user_okpd_codes,
                                user_stop_words=[],  # Без фильтра стоп-слов
                                region_id=region_id,
                                category_id=category_id,
                                limit=1000
                            )
                            okpd_total = len(all_with_okpd) if all_with_okpd else 0
                            stop_words_total = okpd_total
                            stop_words_filtered = section_counts.get('purchases_44fz_new', 0)
                            okpd_filtered = okpd_total  # OKPD фильтр уже применен в get_user_okpd_codes
                        except Exception as e:
                            logger.warning(f"Не удалось получить статистику фильтрации: {e}")

                    self.dashboard.update_filtering_stats(
                        okpd_filtered=okpd_filtered,
                        okpd_total=okpd_total,
                        stop_words_filtered=stop_words_filtered,
                        stop_words_total=stop_words_total
                    )
                    logger.info(f"Обновлена статистика фильтрации: OKPD {okpd_filtered}/{okpd_total}, Стоп-слова {stop_words_filtered}/{stop_words_total}")
                except Exception as e:
                    logger.warning(f"Ошибка обновления статистики фильтрации: {e}")

            # Обновляем счетчики на Dashboard
            if hasattr(self, 'dashboard') and self.dashboard:
                for section_id, count in section_counts.items():
                    self.dashboard.update_tile_count(section_id, count)
                    logger.info(f"Обновлен счетчик для {section_id}: {count}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении счетчиков на Dashboard: {e}", exc_info=True)
    
    def _on_dashboard_section_selected(self, section_id: str):
        """
        Обработка выбора раздела на Dashboard.
        
        Args:
            section_id: ID раздела ('purchases_44fz_new', 'purchases_223fz_new', и т.д.)
        """
        # Переключаемся на страницу с вкладками
        self.stack_widget.setCurrentIndex(1)
        
        # Определяем индекс вкладки для выбранного раздела
        tab_map = {
            'purchases_44fz_new': 0,
            'purchases_223fz_new': 1,
            'purchases_44fz_won': 2,
            'purchases_223fz_won': 3,
            'purchases_44fz_commission': 4,
            'purchases_in_work': 5,  # Если есть вкладка "В работе"
        }
        
        title_map = {
            'purchases_44fz_new': "Новые закупки 44ФЗ",
            'purchases_223fz_new': "Новые закупки 223ФЗ",
            'purchases_44fz_won': "Разыгранные закупки 44ФЗ",
            'purchases_223fz_won': "Разыгранные закупки 223ФЗ",
            'purchases_44fz_commission': "Работа комиссии 44 ФЗ",
        }
        
        tab_index = tab_map.get(section_id, 0)
        
        # Устанавливаем текущий раздел и заголовок
        self.current_section_id = section_id
        self.current_section_title = title_map.get(section_id, "")
        
        # Получаем виджет вкладки и сохраняем
        if hasattr(self, '_tabs_widget'):
            widget = self._tabs_widget.widget(tab_index)
            self.current_widget = widget
        
        # Переключаем вкладку (это также вызовет _on_tab_changed)
        self._tabs_widget.setCurrentIndex(tab_index)
        
        # Скрываем табы (заголовки вкладок), чтобы показывалось только содержимое нужной вкладки
        # Делаем это ПОСЛЕ установки текущей вкладки, чтобы содержимое было видимым
        if hasattr(self, '_tabs_widget'):
            tab_bar = self._tabs_widget.tabBar()
            if tab_bar:
                # Используем только установку высоты, без изменения стиля
                tab_bar.setMaximumHeight(0)
                tab_bar.setMinimumHeight(0)
        
        # Сохраняем текущий раздел
        self.current_section_id = section_id
        
        # Получаем виджет для загрузки данных
        widget = None
        if hasattr(self, '_tabs_widget'):
            widget = self._tabs_widget.widget(tab_index)
        
        if widget:
            self._load_section_data(section_id, widget)
    
    def _on_back_to_dashboard(self):
        """Обработка возврата на Dashboard"""
        # Показываем табы обратно - восстанавливаем высоту tabBar
        if hasattr(self, '_tabs_widget'):
            tab_bar = self._tabs_widget.tabBar()
            if tab_bar:
                # Восстанавливаем стандартную высоту
                tab_bar.setMaximumHeight(16777215)  # Qt default
                tab_bar.setMinimumHeight(0)
        
        # Переключаемся на Dashboard
        self.stack_widget.setCurrentIndex(0)
    
    def _on_tab_changed(self, index: int):
        """
        Обработка переключения вкладок.
        
        Args:
            index: Индекс вкладки
        """
        # Маппинг индекса вкладки на section_id и заголовки
        section_map = {
            0: 'purchases_44fz_new',
            1: 'purchases_223fz_new',
            2: 'purchases_44fz_won',
            3: 'purchases_223fz_won',
            4: 'purchases_44fz_commission',
        }
        
        title_map = {
            0: "Новые закупки 44ФЗ",
            1: "Новые закупки 223ФЗ",
            2: "Разыгранные закупки 44ФЗ",
            3: "Разыгранные закупки 223ФЗ",
            4: "Работа комиссии 44 ФЗ",
        }
        
        section_id = section_map.get(index)
        if section_id:
            logger.info(f"Вкладка {index} -> section_id: {section_id}")
            self.current_section_id = section_id
            self.current_section_title = title_map.get(index, "")
            
            # Обновляем статус в кэше
            if hasattr(self, 'search_params_cache') and self.search_params_cache:
                self.search_params_cache.current_section_id = section_id
            
            # Получаем виджет вкладки и загружаем закупки
            widget = None
            if hasattr(self, '_tabs_widget'):
                widget = self._tabs_widget.widget(index)
            elif hasattr(self, 'tabs_widget'):
                widget = self.tabs_widget.widget(index)
            
            # Сохраняем текущий виджет
            self.current_widget = widget
            
            # Загружаем данные через менеджер (TenderListWidget не имеет метода load_tenders)
            if widget and section_id:
                logger.debug(f"Загружаем данные для вкладки {index} ({section_id}): {type(widget).__name__}")
                try:
                    self._load_section_data(section_id, widget)
                except Exception as e:
                    logger.error(f"Ошибка при загрузке данных раздела {section_id} для вкладки {index}: {e}", exc_info=True)
            elif not widget:
                logger.warning(f"Виджет вкладки {index} не найден")
            elif not section_id:
                logger.warning(f"Не определен section_id для вкладки {index}")
    
    
    def show_section(self, section_id: str):
        """
        Показ нужного раздела закупок (через StackWidget + Tabs).
        
        Args:
            section_id: ID раздела ('purchases_44fz_new', 'purchases_44fz_won', и т.д.)
        """
        tab_map = {
            'purchases_44fz_new': 0,
            'purchases_223fz_new': 1,
            'purchases_44fz_won': 2,
            'purchases_223fz_won': 3,
            'purchases_44fz_commission': 4,
        }
        
        title_map = {
            'purchases_44fz_new': "Новые закупки 44ФЗ",
            'purchases_223fz_new': "Новые закупки 223ФЗ",
            'purchases_44fz_won': "Разыгранные закупки 44ФЗ",
            'purchases_223fz_won': "Разыгранные закупки 223ФЗ",
            'purchases_44fz_commission': "Работа комиссии 44 ФЗ",
        }
        
        tab_index = tab_map.get(section_id)
        if tab_index is None:
            logger.warning(f"Неизвестный раздел: {section_id}")
            return
        
        # Переключаемся на страницу с разделами и нужную вкладку
        if hasattr(self, 'stack_widget'):
            self.stack_widget.setCurrentIndex(1)  # 1 = страница с вкладками
        if hasattr(self, '_tabs_widget'):
            self._tabs_widget.setCurrentIndex(tab_index)
        
        # Сохраняем текущий раздел и виджет
        self.current_section_id = section_id
        self.current_section_title = title_map.get(section_id, section_id)
        
        # Получаем и сохраняем виджет вкладки
        if hasattr(self, '_tabs_widget'):
            widget = self._tabs_widget.widget(tab_index)
            self.current_widget = widget
    
    def _autoload_tenders_if_settings_saved(self):
        """Автозагрузка закупок, если пользователь ранее сохранил настройки"""
        try:
            # Проверяем, были ли настройки сохранены
            if hasattr(self, 'search_params_cache') and self.search_params_cache:
                if self.search_params_cache.is_settings_saved():
                    logger.info("Настройки были сохранены ранее, но НЕ загружаем закупки автоматически")
                    logger.info("Закупки будут загружены при открытии конкретной вкладки")
                    # НЕ загружаем закупки автоматически, остаемся на Dashboard
                    # Пользователь сам выберет нужную вкладку
        except Exception as e:
            logger.error(f"Ошибка при проверке автозагрузки: {e}", exc_info=True)
    
    def handle_show_tenders(self):
        """Открыть BidsWidget и показать раздел с новыми 44ФЗ."""
        section_id = 'purchases_44fz_new'
        self.show_section(section_id)
        
        # Получаем виджет раздела после переключения
        target_widget = None
        if hasattr(self, '_tabs_widget'):
            current_tab_index = self._tabs_widget.currentIndex()
            target_widget = self._tabs_widget.widget(current_tab_index)
        
        if not target_widget:
            logger.warning(f"Не удалось получить виджет для раздела {section_id}")
            return
        
        # Загружаем данные если еще не загружены или если force=True
        # force=True означает, что нужно перезагрузить данные (например, после изменения фильтров)
        force_reload = getattr(self, '_force_reload', False)
        if not getattr(target_widget, '_loaded', False) or force_reload:
            self._load_section_data(section_id, target_widget)
            # Сбрасываем флаг после загрузки
            if force_reload:
                self._force_reload = False
    
    def _load_section_data(self, section_id: str, widget):
        """Загрузка данных для раздела"""
        # Получаем категорию из кэша для логирования
        category_id = self.search_params_cache.get_category_id()
        logger.info(f"Загрузка данных для раздела {section_id}, категория из кэша: {category_id}")
        category_filter_combo = None  # Будет None, т.к. настройки в подменю
        
        if section_id == 'purchases_44fz_new':
            self.tender_loader_manager.load_tenders_44fz(
                widget=widget,
                user_id=self.current_user_id,
                category_filter_combo=category_filter_combo,
                force=False,
                parent_widget=self
            )
        elif section_id == 'purchases_223fz_new':
            self.tender_loader_manager.load_tenders_223fz(
                widget=widget,
                user_id=self.current_user_id,
                category_filter_combo=category_filter_combo,
                force=False,
                parent_widget=self
            )
        elif section_id == 'purchases_44fz_won':
            self.tender_loader_manager.load_won_tenders_44fz(
                widget=widget,
                user_id=self.current_user_id,
                category_filter_combo=category_filter_combo,
                force=False,
                parent_widget=self
            )
        elif section_id == 'purchases_223fz_won':
            self.tender_loader_manager.load_won_tenders_223fz(
                widget=widget,
                user_id=self.current_user_id,
                category_filter_combo=category_filter_combo,
                force=False,
                parent_widget=self
            )
        elif section_id == 'purchases_44fz_commission':
            self.tender_loader_manager.load_commission_tenders_44fz(
                widget=widget,
                user_id=self.current_user_id,
                category_filter_combo=category_filter_combo,
                force=False,
                parent_widget=self
            )
    
    def on_tender_selection_changed(self):
        """Обработка изменения выбора закупок"""
        # Активируем кнопку "Анализ выбранных" если есть выбранные закупки
        if self.current_widget and hasattr(self.current_widget, 'get_selected_tenders'):
            selected = self.current_widget.get_selected_tenders()
            self.analyze_button.setEnabled(len(selected) > 0)
        else:
            self.analyze_button.setEnabled(False)
    
    def handle_analyze_selected_tenders(self):
        """Обработка нажатия кнопки 'Анализ выбранных'"""
        if not self.current_widget:
            return
        
        # Получаем выбранные закупки из текущего виджета
        selected = []
        if hasattr(self.current_widget, 'get_selected_tenders'):
            selected = self.current_widget.get_selected_tenders()
        
        if not selected:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы одну закупку для анализа")
            return
        
        # Определяем тип реестра и закупок по текущему разделу
        registry_type = None
        tender_type = 'new'
        
        if self.current_section_id == 'purchases_44fz_new':
            registry_type = '44fz'
            tender_type = 'new'
        elif self.current_section_id == 'purchases_223fz_new':
            registry_type = '223fz'
            tender_type = 'new'
        elif self.current_section_id == 'purchases_44fz_won':
            registry_type = '44fz'
            tender_type = 'won'
        elif self.current_section_id == 'purchases_223fz_won':
            registry_type = '223fz'
            tender_type = 'won'
        elif self.current_section_id == 'purchases_44fz_commission':
            registry_type = '44fz'
            tender_type = 'commission'
        
        # Определяем правильные виджеты для передачи в анализатор
        # Анализатор использует current_tab_text для определения откуда брать выбранные закупки
        # Поэтому передаем текущий виджет в соответствующее поле
        won_tenders_44fz_widget = None
        won_tenders_223fz_widget = None
        commission_tenders_44fz_widget = None
        
        if registry_type == '44fz':
            if tender_type == 'new':
                tenders_44fz_widget = self.current_widget
                tenders_223fz_widget = self.tenders_223fz_widget
            elif tender_type == 'won':
                tenders_44fz_widget = self.tenders_44fz_widget
                tenders_223fz_widget = self.tenders_223fz_widget
                won_tenders_44fz_widget = self.current_widget
            else:  # commission
                tenders_44fz_widget = self.tenders_44fz_widget
                tenders_223fz_widget = self.tenders_223fz_widget
                commission_tenders_44fz_widget = self.current_widget
        else:  # 223fz
            if tender_type == 'new':
                tenders_44fz_widget = self.tenders_44fz_widget
                tenders_223fz_widget = self.current_widget
            elif tender_type == 'won':
                tenders_44fz_widget = self.tenders_44fz_widget
                tenders_223fz_widget = self.tenders_223fz_widget
                won_tenders_223fz_widget = self.current_widget
        
        # Вызываем метод анализатора
        self.document_analyzer.handle_analyze_selected_tenders(
            tenders_44fz_widget=tenders_44fz_widget,
            tenders_223fz_widget=tenders_223fz_widget,
            won_tenders_44fz_widget=won_tenders_44fz_widget,
            won_tenders_223fz_widget=won_tenders_223fz_widget,
            commission_tenders_44fz_widget=commission_tenders_44fz_widget,
            current_tab_text=self.current_section_title or "",
            parent_widget=self
        )
    
    def handle_analyze_all_tenders(self):
        """Обработка нажатия кнопки 'Анализировать все' - запускает анализ для текущей вкладки"""
        if not self.current_widget:
            logger.warning("Не удалось запустить анализ: current_widget не установлен")
            return
        
        # Определяем тип реестра и закупок по текущему разделу
        registry_type = None
        tender_type = 'new'
        current_tab_text = ""
        
        if self.current_section_id == 'purchases_44fz_new':
            registry_type = '44fz'
            tender_type = 'new'
            current_tab_text = "Новые закупки 44ФЗ"
        elif self.current_section_id == 'purchases_223fz_new':
            registry_type = '223fz'
            tender_type = 'new'
            current_tab_text = "Новые закупки 223ФЗ"
        elif self.current_section_id == 'purchases_44fz_won':
            registry_type = '44fz'
            tender_type = 'won'
            current_tab_text = "Разыгранные закупки 44ФЗ"
        elif self.current_section_id == 'purchases_223fz_won':
            registry_type = '223fz'
            tender_type = 'won'
            current_tab_text = "Разыгранные закупки 223ФЗ"
        elif self.current_section_id == 'purchases_44fz_commission':
            registry_type = '44fz'
            tender_type = 'commission'
            current_tab_text = "Работа комиссии 44 ФЗ"
        
        # #region agent log ANALYZE_ALL_TRIGGER
        import json
        import time
        log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "analysis-trigger",
                    "hypothesisId": "analyze-all",
                    "location": "widget.py:handle_analyze_all_tenders",
                    "message": "ANALYZE_ALL_TRIGGER",
                    "data": {
                        "current_section_id": self.current_section_id,
                        "registry_type": registry_type,
                        "tender_type": tender_type,
                        "has_current_widget": self.current_widget is not None
                    },
                    "timestamp": int(time.time() * 1000)
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion

        # Вызываем метод анализатора для текущей вкладки
        self.document_analyzer.handle_analyze_all_tenders(
            tenders_44fz_widget=self.tenders_44fz_widget,
            tenders_223fz_widget=self.tenders_223fz_widget,
            won_tenders_44fz_widget=self.won_tenders_44fz_widget,
            won_tenders_223fz_widget=self.won_tenders_223fz_widget,
            commission_tenders_44fz_widget=self.commission_tenders_44fz_widget,
            current_tab_text=current_tab_text,
            parent_widget=self
        )
    
    def refresh_current_feed(self):
        """Обновление статусов обработки документов для текущего раздела"""
        # #region agent log
        import json
        import time
        log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "E",
                    "location": "widget.py:refresh_current_feed:entry",
                    "message": "Обновление ленты закупок",
                    "data": {
                        "has_current_widget": self.current_widget is not None,
                        "current_section_id": self.current_section_id
                    },
                    "timestamp": int(time.time() * 1000)
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        if not self.current_widget:
            return
        
        # Перезагружаем данные для текущего раздела
        if self.current_section_id:
            self._load_section_data(self.current_section_id, self.current_widget)
    
    def _handle_db_reconnection(self) -> None:
        """Обработка переподключения к БД с восстановлением параметров"""
        self.db_manager.handle_db_reconnection(
            self,
            self.cache_manager,
            getattr(self, 'settings_tab', None)
        )
        # Обновляем ссылки на репозитории после переподключения
        self.tender_repo = self.db_manager.tender_repo
        self.tender_match_repo = self.db_manager.tender_match_repo
        self.tender_match_repository = self.tender_match_repo
