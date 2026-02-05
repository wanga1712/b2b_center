"""
MODULE: modules.bids.tender_card
RESPONSIBILITY: Display individual tender card with summary and actions.
ALLOWED: PyQt5, typing, loguru, modules.styles.bids_styles, modules.bids.tender_detail_dialog, modules.bids.tender_card_ui.
FORBIDDEN: Direct database modification (except via Managers/Services).
ERRORS: None.

Виджет карточки закупки (сокращенный и полный вид)
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Dict, Any, Optional, TYPE_CHECKING, List
import traceback
from loguru import logger
from modules.styles.bids_styles import apply_tender_checkbox_style
from modules.bids.tender_detail_dialog import TenderDetailDialog

if TYPE_CHECKING:
    from services.document_search_service import DocumentSearchService
    from services.match_services.tender_match_repository_facade import TenderMatchRepositoryFacade as TenderMatchRepository


class TenderCard(QFrame):
    MATCH_DETAILS_CACHE_LIMIT = 20
    selection_changed = pyqtSignal(bool)
    
    def __init__(
        self,
        tender_data: Dict[str, Any],
        document_search_service: Optional['DocumentSearchService'] = None,
        tender_match_repository: Optional['TenderMatchRepository'] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.tender_data = tender_data or {}
        self.document_search_service = document_search_service
        self.tender_match_repository = tender_match_repository
        self._registry_type = self._determine_registry_type()
        self._match_summary_cache: Optional[Dict[str, Any]] = None
        self._match_details_cache: Optional[List[Dict[str, Any]]] = None
        self.matches_preview: Optional[QWidget] = None
        self.is_selected = False
        self._detail_dialog = None  # Защита от повторного открытия
        try:
            self.init_ui()
        except Exception as e:
            logger.error(
                f"Ошибка при инициализации карточки закупки ID {tender_data.get('id', 'неизвестно')}: {repr(e)}"
            )
            logger.error(traceback.format_exc())
            raise
    
    def init_ui(self):
        """Инициализация интерфейса карточки"""
        from modules.bids.tender_card_ui import (
            create_header_layout, create_info_layout,
            create_price_date_layout, create_meta_layout, create_okpd_label,
            create_actions_layout
        )
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Применяем Salesforce стиль с цветовой полоской
        self._apply_salesforce_card_style()
        
        self.select_checkbox = QCheckBox()
        apply_tender_checkbox_style(self.select_checkbox)
        self.select_checkbox.stateChanged.connect(self._on_selection_changed)
        
        # Получаем match_summary для передачи в header
        match_summary = self._fetch_match_summary()
        
        layout.addLayout(create_header_layout(self.tender_data, self.select_checkbox, match_summary))
        layout.addLayout(create_info_layout(self.tender_data))
        layout.addLayout(create_price_date_layout(self.tender_data))
        
        meta_layout = create_meta_layout(self.tender_data)
        if meta_layout:
            layout.addLayout(meta_layout)
        
        okpd_label = create_okpd_label(self.tender_data)
        if okpd_label:
            layout.addWidget(okpd_label)
        
        # Добавляем секцию действий (Salesforce style)
        actions_layout = create_actions_layout(
            self.tender_data,
            match_summary,
            on_convert_clicked=self._on_convert_to_deal
        )
        layout.addLayout(actions_layout)
        
        # Старые статус и превью (опционально, можно убрать если дублируется)
        # from modules.bids.tender_card_status_preview import add_status_and_preview
        # self.status_container, self.matches_preview = add_status_and_preview(
        #     layout, self._create_status_badges, self._create_matches_preview
        # )
        
        self.setMouseTracking(True)
    
    def _apply_salesforce_card_style(self):
        """Применить Salesforce стиль с цветовой полоской."""
        from modules.bids.tender_card_salesforce_styles import get_priority_color, get_salesforce_card_style
        
        match_summary = self._fetch_match_summary()
        priority_color = get_priority_color(self.tender_data, match_summary)
        style = get_salesforce_card_style(priority_color)
        self.setStyleSheet(style)
    
    def _on_convert_to_deal(self):
        """Обработчик конвертации закупки в сделку."""
        from PyQt5.QtWidgets import QMessageBox
        
        result = QMessageBox.question(
            self,
            "Конвертация в сделку",
            f"Конвертировать закупку '{self.tender_data.get('auction_name', 'Без названия')[:50]}...' в сделку?\n\n"
            "Будет создана новая сделка в воронке продаж.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            try:
                self._convert_tender_to_deal()
                QMessageBox.information(
                    self,
                    "Успех",
                    "Закупка успешно конвертирована в сделку!"
                )
            except Exception as e:
                logger.error(f"Ошибка при конвертации закупки в сделку: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось конвертировать закупку в сделку:\n{str(e)}"
                )
    
    def _convert_tender_to_deal(self):
        """Конвертация закупки в сделку (создание записи в sales_deals)."""
        # TODO: Реализовать логику создания сделки из закупки
        # Нужно создать запись в таблице sales_deals с данными из закупки
        logger.info(f"Конвертация закупки ID {self.tender_data.get('id')} в сделку")
        raise NotImplementedError("Конвертация в сделку будет реализована в следующей итерации")
    
    def mouseDoubleClickEvent(self, event):
        """Обработка двойного клика - открытие полной информации"""
        super().mouseDoubleClickEvent(event)
        
        # Защита от повторного открытия диалога
        if self._detail_dialog is not None:
            try:
                if self._detail_dialog.isVisible():
                    self._detail_dialog.raise_()
                    self._detail_dialog.activateWindow()
                    return
            except (RuntimeError, AttributeError):
                # Диалог был удален, сбрасываем ссылку
                self._detail_dialog = None
        
        # Проверяем валидность данных
        if not self.tender_data or not self.tender_data.get('id'):
            logger.error("Не удалось открыть диалог: отсутствуют данные о закупке")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось открыть информацию о закупке: отсутствуют данные"
            )
            return
        
        try:
            # Копируем данные, чтобы избежать проблем с изменением во время работы диалога
            import copy
            tender_data_copy = copy.deepcopy(self.tender_data)
            match_summary_copy = copy.deepcopy(self._match_summary_cache) if self._match_summary_cache else None
            match_details_copy = copy.deepcopy(self._match_details_cache) if self._match_details_cache else None
            
            # Получаем правильный parent (окно приложения)
            parent_window = self.window()
            if parent_window is None:
                from PyQt5.QtWidgets import QApplication
                parent_window = QApplication.activeWindow()
            
            dialog = TenderDetailDialog(
                tender_data_copy,
                document_search_service=self.document_search_service,
                tender_match_repository=self.tender_match_repository,
                registry_type=self._registry_type,
                initial_match_summary=match_summary_copy,
                initial_match_details=match_details_copy,
                parent=parent_window,
            )
            self._detail_dialog = dialog
            dialog.finished.connect(lambda: setattr(self, '_detail_dialog', None))
            dialog.exec_()
        except Exception as e:
            logger.error(
                f"Ошибка при открытии диалога деталей закупки ID {self.tender_data.get('id', 'неизвестно')}: {e}",
                exc_info=True,
            )
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть информацию о закупке:\n{str(e)}"
            )
            self._detail_dialog = None
    
    def _create_status_badges(self) -> Optional[QWidget]:
        from modules.bids.tender_status_badges import create_status_badges
        return create_status_badges(self._fetch_match_summary(), self)
    
    def _create_matches_preview(self) -> Optional[QWidget]:
        from modules.bids.tender_matches_preview import create_matches_preview
        return create_matches_preview(self._fetch_match_summary(), self._fetch_match_details)
    
    def _fetch_match_summary(self) -> Optional[Dict[str, Any]]:
        from modules.bids.tender_card_data_fetch import fetch_match_summary_with_cache
        tender_id = self.tender_data.get('id')
        # #region agent log
        import json
        import time
        log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "B",
                    "location": "tender_card.py:_fetch_match_summary:entry",
                    "message": "Получение match_summary",
                    "data": {
                        "tender_id": tender_id,
                        "has_cache": self._match_summary_cache is not None
                    },
                    "timestamp": int(time.time() * 1000)
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        if self._match_summary_cache is None:
            self._match_summary_cache = fetch_match_summary_with_cache(
                self.tender_match_repository, tender_id, self._registry_type, None
            )
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B",
                        "location": "tender_card.py:_fetch_match_summary:loaded_from_db",
                        "message": "Данные загружены из БД",
                        "data": {
                            "tender_id": tender_id,
                            "match_count": self._match_summary_cache.get('match_count') if self._match_summary_cache else None
                        },
                        "timestamp": int(time.time() * 1000)
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
        else:
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B",
                        "location": "tender_card.py:_fetch_match_summary:using_cache",
                        "message": "Используется кэш (данные могут быть устаревшими)",
                        "data": {
                            "tender_id": tender_id,
                            "match_count": self._match_summary_cache.get('match_count') if self._match_summary_cache else None
                        },
                        "timestamp": int(time.time() * 1000)
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
        return self._match_summary_cache
    
    def _fetch_match_details(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        from modules.bids.tender_card_data_fetch import fetch_match_details_with_cache
        tender_id = self.tender_data.get('id')
        if self._match_details_cache is None and self._fetch_match_summary():
            self._match_details_cache = fetch_match_details_with_cache(
                self.tender_match_repository, tender_id, self._registry_type, None, self.MATCH_DETAILS_CACHE_LIMIT
            )
        return fetch_match_details_with_cache(
            self.tender_match_repository, tender_id, self._registry_type,
            self._match_details_cache, self.MATCH_DETAILS_CACHE_LIMIT, limit
        )
    
    def update_status(self):
        # #region agent log
        import json
        import time
        log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
        tender_id = self.tender_data.get('id')
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "D",
                    "location": "tender_card.py:update_status:entry",
                    "message": "Обновление статуса карточки",
                    "data": {
                        "tender_id": tender_id,
                        "cache_before": self._match_summary_cache is not None
                    },
                    "timestamp": int(time.time() * 1000)
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        from modules.bids.tender_card_update import update_card_status
        update_card_status(self, self._create_status_badges, self._create_matches_preview)
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "D",
                    "location": "tender_card.py:update_status:after",
                    "message": "Статус карточки обновлен (но кэш не очищен)",
                    "data": {
                        "tender_id": tender_id,
                        "cache_after": self._match_summary_cache is not None
                    },
                    "timestamp": int(time.time() * 1000)
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
    
    def _on_selection_changed(self, state: int):
        self.is_selected = (state == Qt.Checked)
        self.selection_changed.emit(self.is_selected)
    
    def set_selected(self, selected: bool):
        if hasattr(self, 'select_checkbox'):
            self.select_checkbox.setChecked(selected)
            self.is_selected = selected
    
    def _determine_registry_type(self) -> str:
        from modules.bids.tender_registry_type import determine_registry_type
        return determine_registry_type(self.tender_data)

