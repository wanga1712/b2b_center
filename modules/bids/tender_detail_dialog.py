"""
Модуль для диалога с полной информацией о закупке.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from PyQt5.QtWidgets import QDialog, QApplication, QMessageBox, QMainWindow
from loguru import logger

if TYPE_CHECKING:
    from services.document_search_service import DocumentSearchService
    from services.tender_match_repository import TenderMatchRepository


class TenderDetailDialog(QDialog):
    """Диалог с полной информацией о закупке"""
    
    def __init__(
        self,
        tender_data: Dict[str, Any],
        document_search_service: Optional['DocumentSearchService'] = None,
        tender_match_repository: Optional['TenderMatchRepository'] = None,
        registry_type: Optional[str] = None,
        initial_match_summary: Optional[Dict[str, Any]] = None,
        initial_match_details: Optional[List[Dict[str, Any]]] = None,
        parent=None,
    ):
        super().__init__(parent)
        
        # Проверяем валидность данных перед инициализацией
        if not tender_data:
            raise ValueError("tender_data не может быть пустым")
        
        self.tender_data = tender_data or {}
        self.document_search_service = document_search_service
        self.tender_match_repository = tender_match_repository
        
        try:
            self.registry_type = registry_type or self._determine_registry_type()
        except Exception as e:
            from loguru import logger
            logger.warning(f"Ошибка при определении типа реестра: {e}, используем '44fz' по умолчанию")
            self.registry_type = '44fz'
        
        self.match_summary = initial_match_summary
        self.match_details = initial_match_details or []
        
        try:
            self.setWindowTitle("Подробная информация о закупке")
            self._set_fullscreen_size()
            self._load_match_data()
            self.init_ui()
        except Exception as e:
            from loguru import logger
            logger.error(f"Ошибка при инициализации диалога деталей закупки: {e}", exc_info=True)
            raise
    
    def _determine_registry_type(self) -> str:
        from modules.bids.tender_detail_dialog_helpers import determine_registry_type
        return determine_registry_type(self.tender_data)
    
    def _set_fullscreen_size(self):
        from modules.bids.tender_detail_dialog_helpers import set_fullscreen_size
        set_fullscreen_size(self)
    
    def _load_match_data(self):
        from modules.bids.tender_detail_dialog_helpers import load_match_data
        tender_id = self.tender_data.get('id')
        self.match_summary, self.match_details = load_match_data(
            self.tender_match_repository,
            tender_id,
            self.registry_type,
            self.match_summary,
            self.match_details
        )
    
    def init_ui(self):
        """Инициализация интерфейса диалога"""
        from modules.bids.tender_detail_dialog_init import init_dialog_ui
        from modules.bids.tender_detail_dialog_download import handle_download_all_documents
        init_dialog_ui(
            self,
            self.tender_data,
            self.match_summary,
            self.match_details,
            lambda links: handle_download_all_documents(self, links, self.tender_data),
            self._handle_mark_uninteresting,
            self._handle_move_to_funnel,
        )
    
    def _handle_mark_uninteresting(self):
        """Пометить тендер как неинтересный и закрыть диалог."""
        if not self.tender_match_repository:
            return
        
        tender_id = self.tender_data.get("id")
        if not tender_id:
            return
        
        registry_type = getattr(self, "registry_type", None)
        if not registry_type:
            return
        
        success = self.tender_match_repository.set_interesting_status(
            tender_id,
            registry_type,
            False,
        )
        if not success:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось пометить закупку как неинтересную.",
            )
            return
        
        QMessageBox.information(
            self,
            "Готово",
            "Закупка помечена как неинтересная и больше не будет показываться в списке новых.",
        )
        self.accept()
    
    def _handle_move_to_funnel(self):
        """Переместить закупку в воронку продаж"""
        # #region agent log
        try:
            from pathlib import Path
            import json
            from datetime import datetime
            log_entry = {
                "sessionId": "debug-session",
                "runId": "pre-fix",
                "hypothesisId": "M1",
                "location": f"{__file__}:_handle_move_to_funnel:entry",
                "message": "Начало перемещения закупки в воронку",
                "data": {
                    "tender_id": self.tender_data.get("id"),
                    "has_registry_type": hasattr(self, "registry_type"),
                },
                "timestamp": int(datetime.now().timestamp() * 1000),
            }
            log_path = Path(__file__).resolve().parents[2] / ".cursor" / "debug.log"
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        from modules.crm.sales_funnel.pipeline_selection_dialog import PipelineSelectionDialog
        from modules.crm.sales_funnel.tender_to_funnel_service import TenderToFunnelService
        from modules.crm.sales_funnel import PipelineRepository, DealRepository
        from core.tender_database import TenderDatabaseManager
        from loguru import logger
        
        tender_id = self.tender_data.get("id")
        if not tender_id:
            QMessageBox.warning(self, "Ошибка", "Не удалось определить ID закупки")
            return
        
        registry_type = getattr(self, "registry_type", None)
        if not registry_type:
            QMessageBox.warning(self, "Ошибка", "Не удалось определить тип реестра")
            return
        
        # #region agent log
        try:
            from pathlib import Path
            import json
            from datetime import datetime
            log_entry = {
                "sessionId": "debug-session",
                "runId": "pre-fix",
                "hypothesisId": "M2",
                "location": f"{__file__}:_handle_move_to_funnel:before_db_manager",
                "message": "Перед получением tender_db_manager",
                "data": {
                    "has_parent": self.parent() is not None,
                    "parent_type": type(self.parent()).__name__ if self.parent() else None,
                },
                "timestamp": int(datetime.now().timestamp() * 1000),
            }
            log_path = Path(__file__).resolve().parents[2] / ".cursor" / "debug.log"
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        # Получаем tender_db_manager из родительского виджета или создаем новый
        tender_db_manager = None
        try:
            if hasattr(self.parent(), 'tender_db_manager'):
                tender_db_manager = self.parent().tender_db_manager
            elif hasattr(self.parent(), 'bids_widget'):
                if hasattr(self.parent().bids_widget, 'tender_db_manager'):
                    tender_db_manager = self.parent().bids_widget.tender_db_manager
        except Exception as e:
            logger.error(f"Ошибка при получении tender_db_manager из parent: {e}")
        
        if not tender_db_manager:
            # Пытаемся получить через DI
            try:
                from core.dependency_injection import container
                tender_db_manager = container.get_tender_database_manager()
            except Exception as e:
                logger.error(f"Не удалось получить tender_db_manager: {e}")
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Не удалось подключиться к базе данных воронок продаж"
                )
                return
        
        # #region agent log
        try:
            from pathlib import Path
            import json
            from datetime import datetime
            log_entry = {
                "sessionId": "debug-session",
                "runId": "pre-fix",
                "hypothesisId": "M3",
                "location": f"{__file__}:_handle_move_to_funnel:after_db_manager",
                "message": "После получения tender_db_manager",
                "data": {
                    "has_db_manager": tender_db_manager is not None,
                },
                "timestamp": int(datetime.now().timestamp() * 1000),
            }
            log_path = Path(__file__).resolve().parents[2] / ".cursor" / "debug.log"
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        # #region agent log
        try:
            from pathlib import Path
            import json
            from datetime import datetime
            log_entry = {
                "sessionId": "debug-session",
                "runId": "pre-fix",
                "hypothesisId": "M4",
                "location": f"{__file__}:_handle_move_to_funnel:before_dialog",
                "message": "Перед открытием диалога выбора воронки",
                "data": {},
                "timestamp": int(datetime.now().timestamp() * 1000),
            }
            log_path = Path(__file__).resolve().parents[2] / ".cursor" / "debug.log"
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        # Открываем диалог выбора воронки
        try:
            dialog = PipelineSelectionDialog(self)
            if dialog.exec_() != QDialog.Accepted:
                return
            
            selected_pipeline = dialog.get_selected_pipeline()
            if not selected_pipeline:
                return
        except Exception as e:
            logger.error(f"Ошибка при открытии диалога выбора воронки: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при открытии диалога: {str(e)}")
            return
        
        # #region agent log
        try:
            from pathlib import Path
            import json
            from datetime import datetime
            log_entry = {
                "sessionId": "debug-session",
                "runId": "pre-fix",
                "hypothesisId": "M5",
                "location": f"{__file__}:_handle_move_to_funnel:after_dialog",
                "message": "После выбора воронки",
                "data": {
                    "selected_pipeline": selected_pipeline.value if selected_pipeline else None,
                },
                "timestamp": int(datetime.now().timestamp() * 1000),
            }
            log_path = Path(__file__).resolve().parents[2] / ".cursor" / "debug.log"
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        # Создаем сервис перемещения
        try:
            pipeline_repo = PipelineRepository(tender_db_manager)
            deal_repo = DealRepository(tender_db_manager)
            service = TenderToFunnelService(pipeline_repo, deal_repo)
        except Exception as e:
            logger.error(f"Ошибка при создании сервисов: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при создании сервисов: {str(e)}")
            return
        
        # Получаем user_id (по умолчанию 1)
        user_id = 1
        if hasattr(self.parent(), 'current_user_id'):
            user_id = self.parent().current_user_id
        elif hasattr(self.parent(), 'bids_widget'):
            if hasattr(self.parent().bids_widget, 'current_user_id'):
                user_id = self.parent().bids_widget.current_user_id
        
        logger.info(f"Перемещение закупки в воронку: user_id={user_id}, pipeline_type={selected_pipeline.value}, tender_id={tender_id}")
        
        # #region agent log
        try:
            from pathlib import Path
            import json
            from datetime import datetime
            log_entry = {
                "sessionId": "debug-session",
                "runId": "pre-fix",
                "hypothesisId": "M6",
                "location": f"{__file__}:_handle_move_to_funnel:before_move",
                "message": "Перед перемещением закупки",
                "data": {
                    "tender_id": tender_id,
                    "registry_type": registry_type,
                    "pipeline_type": selected_pipeline.value,
                    "user_id": user_id,
                },
                "timestamp": int(datetime.now().timestamp() * 1000),
            }
            log_path = Path(__file__).resolve().parents[2] / ".cursor" / "debug.log"
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        # Перемещаем закупку в воронку
        try:
            deal_id = service.move_tender_to_funnel(
                tender_id=tender_id,
                registry_type=registry_type,
                pipeline_type=selected_pipeline,
                user_id=user_id,
                tender_data=self.tender_data
            )
            
        except Exception as e:
            logger.error(f"Ошибка при перемещении закупки в воронку: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при перемещении закупки: {str(e)}")
            return
        
        if deal_id:
            # Помечаем закупку как перемещенную (не показывать в разделе Закупки)
            if self.tender_match_repository:
                self.tender_match_repository.set_interesting_status(
                    tender_id,
                    registry_type,
                    False,  # Помечаем как неинтересную для раздела Закупки
                )
            
            # Обновляем виджет воронки и переключаемся на него
            self._refresh_and_show_funnel(selected_pipeline)
            
            pipeline_names = {
                'participation': 'Участие в торгах',
                'materials_supply': 'Поставка материалов',
                'subcontracting': 'Субподрядные работы',
            }
            pipeline_name = pipeline_names.get(selected_pipeline.value, selected_pipeline.value)
            
            QMessageBox.information(
                self,
                "Готово",
                f"Закупка перемещена в воронку '{pipeline_name}'.\n"
                f"Она больше не будет показываться в разделе Закупки.\n"
                f"Вы переключены на воронку продаж."
            )
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось переместить закупку в воронку продаж."
            )
    
    def _refresh_and_show_funnel(self, pipeline_type):
        """Обновить виджет воронки и переключиться на него"""
        try:
            # Находим MainWindow через родителя
            main_window = self.parent()
            while main_window and not isinstance(main_window, QMainWindow):
                main_window = main_window.parent()
            
            if not main_window:
                logger.warning("Не удалось найти MainWindow для обновления воронки")
                return
            
            # Импортируем PipelineType для сравнения
            from modules.crm.sales_funnel.models import PipelineType
            
            # Определяем, какой виджет воронки нужно обновить
            funnel_widget = None
            if pipeline_type == PipelineType.PARTICIPATION:
                funnel_widget = getattr(main_window, 'sales_funnel_participation', None)
            elif pipeline_type == PipelineType.MATERIALS_SUPPLY:
                funnel_widget = getattr(main_window, 'sales_funnel_materials', None)
            elif pipeline_type == PipelineType.SUBCONTRACTING:
                funnel_widget = getattr(main_window, 'sales_funnel_subcontracting', None)
            
            if funnel_widget:
                # Обновляем данные воронки
                funnel_widget.load_data()
                logger.info(f"Виджет воронки {pipeline_type.value} обновлен")
                
                # Переключаемся на виджет воронки в стеке
                if hasattr(main_window, 'stacked'):
                    index = main_window.stacked.indexOf(funnel_widget)
                    if index >= 0:
                        main_window.stacked.setCurrentWidget(funnel_widget)
                        logger.info(f"Переключено на виджет воронки {pipeline_type.value}")
                    else:
                        logger.warning(f"Виджет воронки {pipeline_type.value} не найден в стеке")
            else:
                logger.warning(f"Виджет воронки {pipeline_type.value} не найден в MainWindow")
        except Exception as e:
            logger.error(f"Ошибка при обновлении виджета воронки: {e}", exc_info=True)

