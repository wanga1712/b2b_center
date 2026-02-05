from typing import Optional, Dict, Any
from PyQt5.QtWidgets import QMessageBox
from loguru import logger


class ActionHandlers:
    """Обработчики действий для диалога детальной информации о тендере"""
    
    @staticmethod
    def handle_mark_uninteresting(
        tender_match_repository,
        tender_data: Dict[str, Any],
        registry_type: Optional[str] = None
    ) -> bool:
        """
        Пометить тендер как неинтересный.
        
        Args:
            tender_match_repository: Репозиторий для работы с совпадениями тендеров
            tender_data: Данные тендера
            registry_type: Тип реестра
            
        Returns:
            bool: True если операция успешна, False в противном случае
        """
        if not tender_match_repository:
            logger.warning("TenderMatchRepository не предоставлен для mark_uninteresting")
            return False
        
        tender_id = tender_data.get("id")
        if not tender_id:
            logger.warning("Не удалось получить ID тендера из данных")
            return False
        
        # Если registry_type не предоставлен, пытаемся определить из данных
        actual_registry_type = registry_type
        if not actual_registry_type:
            actual_registry_type = tender_data.get("registry_type", "44fz")
        
        success = tender_match_repository.set_interesting_status(
            tender_id,
            actual_registry_type,
            False,  # Пометить как неинтересный
        )
        
        if not success:
            logger.error(f"Не удалось пометить тендер {tender_id} как неинтересный")
            
        return success
    
    @staticmethod
    def show_mark_uninteresting_result(success: bool, parent_widget=None):
        """
        Показать результат операции пометки как неинтересный.
        
        Args:
            success: Результат операции
            parent_widget: Родительский виджет для диалогов
        """
        if success:
            QMessageBox.information(
                parent_widget,
                "Готово",
                "Закупка помечена как неинтересная и больше не будет показываться в списке новых.",
            )
        else:
            QMessageBox.warning(
                parent_widget,
                "Ошибка",
                "Не удалось пометить закупку как неинтересную.",
            )

    @staticmethod
    def handle_move_to_funnel(
        tender_data: Dict[str, Any],
        registry_type: Optional[str] = None,
        parent_widget=None,
        tender_match_repository=None
    ) -> Optional[int]:
        """
        Переместить закупку в воронку продаж.
        
        Args:
            tender_data: Данные тендера
            registry_type: Тип реестра
            parent_widget: Родительский виджет для диалогов
            tender_match_repository: Репозиторий для пометки статуса
            
        Returns:
            Optional[int]: ID созданной сделки или None при ошибке
        """
        from modules.crm.sales_funnel.pipeline_selection_dialog import PipelineSelectionDialog
        from modules.crm.sales_funnel.tender_to_funnel_service import TenderToFunnelService
        from modules.crm.sales_funnel import PipelineRepository, DealRepository
        from core.tender_database import TenderDatabaseManager
        
        tender_id = tender_data.get("id")
        if not tender_id:
            logger.warning("Не удалось определить ID закупки")
            QMessageBox.warning(parent_widget, "Ошибка", "Не удалось определить ID закупки")
            return None
        
        actual_registry_type = registry_type or tender_data.get("registry_type")
        if not actual_registry_type:
            logger.warning("Не удалось определить тип реестра")
            QMessageBox.warning(parent_widget, "Ошибка", "Не удалось определить тип реестра")
            return None
        
        # Получаем tender_db_manager
        tender_db_manager = ActionHandlers._get_tender_db_manager(parent_widget)
        if not tender_db_manager:
            QMessageBox.warning(
                parent_widget,
                "Ошибка",
                "Не удалось подключиться к базе данных воронок продаж"
            )
            return None
        
        # Открываем диалог выбора воронки
        try:
            dialog = PipelineSelectionDialog(parent_widget)
            if dialog.exec_() != PipelineSelectionDialog.Accepted:
                return None
            
            selected_pipeline = dialog.get_selected_pipeline()
            if not selected_pipeline:
                return None
        except Exception as e:
            logger.error(f"Ошибка при открытии диалога выбора воронки: {e}", exc_info=True)
            QMessageBox.critical(parent_widget, "Ошибка", f"Ошибка при открытии диалога: {str(e)}")
            return None
        
        # Создаем сервис перемещения
        try:
            pipeline_repo = PipelineRepository(tender_db_manager)
            deal_repo = DealRepository(tender_db_manager)
            service = TenderToFunnelService(pipeline_repo, deal_repo)
        except Exception as e:
            logger.error(f"Ошибка при создании сервисов: {e}", exc_info=True)
            QMessageBox.critical(parent_widget, "Ошибка", f"Ошибка при создании сервисов: {str(e)}")
            return None
        
        # Получаем user_id
        user_id = ActionHandlers._get_user_id(parent_widget)
        
        logger.info(f"Перемещение закупки в воронку: user_id={user_id}, pipeline_type={selected_pipeline.value}, tender_id={tender_id}")
        
        # Перемещаем закупку в воронку
        try:
            deal_id = service.move_tender_to_funnel(
                tender_id=tender_id,
                registry_type=actual_registry_type,
                pipeline_type=selected_pipeline,
                user_id=user_id,
                tender_data=tender_data
            )
            
        except Exception as e:
            logger.error(f"Ошибка при перемещении закупки в воронку: {e}", exc_info=True)
            QMessageBox.critical(parent_widget, "Ошибка", f"Ошибка при перемещении закупки: {str(e)}")
            return None
        
        if deal_id:
            # Помечаем закупку как перемещенную (не показывать в разделе Закупки)
            if tender_match_repository:
                tender_match_repository.set_interesting_status(
                    tender_id,
                    actual_registry_type,
                    False,  # Помечаем как неинтересную для раздела Закупки
                )
            
            # Показываем сообщение об успехе
            pipeline_names = {
                'participation': 'Участие в торгах',
                'materials_supply': 'Поставка материалов',
                'subcontracting': 'Субподрядные работы',
            }
            pipeline_name = pipeline_names.get(selected_pipeline.value, selected_pipeline.value)
            
            QMessageBox.information(
                parent_widget,
                "Готово",
                f"Закупка перемещена в воронку '{pipeline_name}'.\n"
                f"ID сделки: {deal_id}"
            )
            
            return deal_id
        
        return None
    
    @staticmethod
    def _get_tender_db_manager(parent_widget) -> Optional[TenderDatabaseManager]:
        """Получить менеджер базы данных тендеров"""
        from core.dependency_injection import container
        
        # Пытаемся получить из родительского виджета
        try:
            if hasattr(parent_widget, 'tender_db_manager'):
                return parent_widget.tender_db_manager
            elif hasattr(parent_widget, 'bids_widget'):
                if hasattr(parent_widget.bids_widget, 'tender_db_manager'):
                    return parent_widget.bids_widget.tender_db_manager
        except Exception as e:
            logger.error(f"Ошибка при получении tender_db_manager из parent: {e}")
        
        # Пытаемся получить через DI
        try:
            return container.get_tender_database_manager()
        except Exception as e:
            logger.error(f"Не удалось получить tender_db_manager через DI: {e}")
            return None
    
    @staticmethod
    def _get_user_id(parent_widget) -> int:
        """Получить ID пользователя"""
        # По умолчанию 1
        user_id = 1
        
        try:
            if hasattr(parent_widget, 'current_user_id'):
                user_id = parent_widget.current_user_id
            elif hasattr(parent_widget, 'bids_widget'):
                if hasattr(parent_widget.bids_widget, 'current_user_id'):
                    user_id = parent_widget.bids_widget.current_user_id
        except Exception as e:
            logger.error(f"Ошибка при получении user_id из parent: {e}")
        
        return user_id