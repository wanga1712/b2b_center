"""
Виджет списка карточек закупок с индикатором загрузки
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame, QLabel
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from typing import List, Dict, Any, Callable, Optional
from loguru import logger

from modules.bids.tender_card import TenderCard
from modules.styles.general_styles import (
    apply_label_style, apply_frame_style, apply_scroll_area_style,
    apply_text_color
)
from services.document_search_service import DocumentSearchService
from typing import TYPE_CHECKING
import json
import os
from pathlib import Path
from datetime import datetime

if TYPE_CHECKING:
    from services.tender_match_repository import TenderMatchRepository

# #region agent log
DEBUG_LOG_PATH = Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
# #endregion


class TenderListWidget(QWidget):
    """
    Виджет списка карточек закупок с прокруткой и индикатором загрузки
    """
    
    def __init__(
        self,
        parent=None,
        document_search_service: Optional[DocumentSearchService] = None,
        tender_match_repository: Optional['TenderMatchRepository'] = None,
    ):
        super().__init__(parent)
        self.tender_cards: List[TenderCard] = []
        self.document_search_service = document_search_service
        self.tender_match_repository = tender_match_repository
        self._loaded = False  # Флаг, что данные были загружены после "Показать тендеры"
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Счетчик загруженных закупок (вверху, вне scroll_area)
        self.count_info = QLabel()
        apply_label_style(self.count_info, 'info_box_small')
        self.count_info.hide()  # Скрыт по умолчанию
        layout.addWidget(self.count_info)
        
        # Прокручиваемая область
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        apply_scroll_area_style(self.scroll_area, 'subtle')
        
        # Контейнер для карточек
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(12)
        self.cards_layout.setContentsMargins(15, 15, 15, 15)
        
        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area)
        
        # Индикатор загрузки (скрыт по умолчанию)
        self.loading_indicator = self._create_loading_indicator()
        self.cards_layout.addWidget(self.loading_indicator)
        self.loading_indicator.hide()
    
    def _create_loading_indicator(self) -> QFrame:
        """Создание индикатора загрузки"""
        frame = QFrame()
        apply_frame_style(frame, 'panel')
        
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignCenter)
        
        # Анимированный текст (можно заменить на QProgressBar или QMovie)
        loading_label = QLabel("⏳ Загрузка закупок...")
        apply_label_style(loading_label, 'h2')
        apply_text_color(loading_label, 'primary')
        loading_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(loading_label)
        
        return frame
    
    def show_loading(self):
        """Показать индикатор загрузки"""
        self.clear_cards()
        self.loading_indicator.show()
        self.cards_layout.addWidget(self.loading_indicator)
    
    def hide_loading(self):
        """Скрыть индикатор загрузки"""
        self.loading_indicator.hide()
        self.cards_layout.removeWidget(self.loading_indicator)
    
    def clear_cards(self):
        """Очистить все карточки"""
        for card in self.tender_cards:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self.tender_cards.clear()
    
    def add_tender_card(self, tender_data: Dict[str, Any]):
        """Добавить карточку закупки"""
        try:
            card = TenderCard(
                tender_data,
                document_search_service=self.document_search_service,
                tender_match_repository=self.tender_match_repository,
                parent=self,
            )
            # Подключаем сигнал изменения выбора
            if hasattr(card, 'selection_changed'):
                card.selection_changed.connect(self._on_card_selection_changed)
            self.tender_cards.append(card)
            self.cards_layout.addWidget(card)
        except Exception as e:
            logger.error(f"Ошибка при создании карточки закупки: {e}")
            logger.error(f"Данные закупки: {tender_data.get('id', 'нет ID')}")
    
    def _load_match_summaries_batch(self, tenders: List[Dict[str, Any]]) -> Dict[tuple, Dict[str, Any]]:
        """
        Загрузка всех match_summary батчем для оптимизации
        
        Returns:
            Словарь {(tender_id, registry_type): match_summary}
        """
        if not self.tender_match_repository or not tenders:
            return {}
        
        # Группируем тендеры по registry_type
        tenders_by_registry = {}
        for tender in tenders:
            tender_id = tender.get('id')
            if not tender_id:
                continue
            
            registry_type = '44fz'  # По умолчанию
            if 'registry_type' in tender:
                registry_type = tender['registry_type']
            elif 'platform' in tender:
                platform = str(tender['platform']).lower()
                if '223' in platform or 'закон' in platform:
                    registry_type = '223fz'
            
            if registry_type not in tenders_by_registry:
                tenders_by_registry[registry_type] = []
            tenders_by_registry[registry_type].append(tender_id)
        
        # Загружаем батчем для каждого registry_type
        cache = {}
        for registry_type, tender_ids in tenders_by_registry.items():
            try:
                # Загружаем match_results батчем
                match_results = self.tender_match_repository.get_match_results_batch(tender_ids, registry_type)
                
                # Для каждого результата вычисляем summary
                for tender_id, match_result in match_results.items():
                    # Вычисляем summary локально (аналогично get_match_summary)
                    match_summary = self._compute_match_summary(match_result, tender_id, registry_type)
                    if match_summary:
                        cache[(tender_id, registry_type)] = match_summary
            except Exception as e:
                logger.error(f"Ошибка при батч-загрузке match_results для {registry_type}: {e}")
        
        return cache
    
    def _compute_match_summary(self, match_result: Dict[str, Any], tender_id: int, registry_type: str) -> Optional[Dict[str, Any]]:
        """Вычисление match_summary из match_result (локально, без запросов к БД)"""
        if not match_result:
            return None
        
        # Для упрощения, если нет детальной информации о совпадениях, используем match_percentage
        match_percentage = match_result.get('match_percentage', 0)
        match_count = match_result.get('match_count', 0)
        
        # Определяем типы совпадений на основе процента
        exact_count = 1 if match_percentage >= 100 else 0
        good_count = 1 if 85 <= match_percentage < 100 else 0
        brown_count = 1 if 56 <= match_percentage < 85 else 0
        
        return {
            'match_result': match_result,
            'exact_count': exact_count,
            'good_count': good_count,
            'brown_count': brown_count,
            'total_count': match_count,
            'error_reason': match_result.get('error_reason'),
        }
    
    def _get_tender_priority_cached(self, tender: Dict[str, Any], cache: Dict[tuple, Dict[str, Any]]) -> int:
        """Получение приоритета тендера с использованием кэша"""
        tender_id = tender.get('id')
        if not tender_id:
            return 999
        
        # Определяем registry_type
        registry_type = '44fz'  # По умолчанию
        if 'registry_type' in tender:
            registry_type = tender['registry_type']
        elif 'platform' in tender:
            platform = str(tender['platform']).lower()
            if '223' in platform or 'закон' in platform:
                registry_type = '223fz'
        
        # Получаем из кэша
        match_summary = cache.get((tender_id, registry_type))
        
        if not match_summary:
            return 5  # Не обработано
        
        error_reason = match_summary.get('error_reason')
        if error_reason:
            return 6  # Ошибка обработки
        
        exact_count = match_summary.get('exact_count', 0)
        good_count = match_summary.get('good_count', 0)
        brown_count = match_summary.get('brown_count', 0)
        
        # Приоритет 1: Только зеленые (100%)
        if exact_count > 0 and good_count == 0 and brown_count == 0:
            return 1
        
        # Приоритет 2: Зеленые + желтые
        if exact_count > 0 and good_count > 0:
            return 2
        
        # Приоритет 3: Желтые + серые или только желтые
        if exact_count == 0 and good_count > 0:
            return 3
        
        # Приоритет 4: Только серые
        if brown_count > 0 and exact_count == 0 and good_count == 0:
            return 4
        
        return 999
    
    def _get_tender_priority(self, tender: Dict[str, Any]) -> int:
        """
        Определение приоритета карточки для сортировки.
        
        Возвращает число: меньше = выше приоритет (выводятся первыми).
        
        Приоритеты (по порядку вывода):
        1. Только зеленые (100%) - exact_count > 0, good_count == 0, brown_count == 0
        2. Зеленые + желтые (100% и 85%+) - exact_count > 0, good_count > 0
        3. Желтые + серые (85%+ и 56%+) - exact_count == 0, good_count > 0, brown_count > 0
        4. Только серые (56%+) - brown_count > 0, exact_count == 0, good_count == 0
        5. Не обработано (summary is None)
        6. Ошибка обработки (error_reason)
        """
        tender_id = tender.get('id')
        if not tender_id:
            return 999  # Самый низкий приоритет
        
        # Получаем match_summary для определения приоритета
        match_summary = None
        if self.tender_match_repository:
            try:
                # Определяем тип реестра из данных тендера
                registry_type = '44fz'  # По умолчанию
                if 'registry_type' in tender:
                    registry_type = tender['registry_type']
                elif 'platform' in tender:
                    platform = str(tender['platform']).lower()
                    if '223' in platform or 'закон' in platform:
                        registry_type = '223fz'
                
                match_summary = self.tender_match_repository.get_match_summary(tender_id, registry_type)
            except Exception as e:
                logger.debug(f"Не удалось получить match_summary для тендера {tender_id}: {e}")
        
        if not match_summary:
            return 5  # Не обработано - 5-й приоритет
        
        error_reason = match_summary.get('error_reason')
        if error_reason:
            return 6  # Ошибка обработки - 6-й приоритет (последний)
        
        exact_count = match_summary.get('exact_count', 0)
        good_count = match_summary.get('good_count', 0)
        brown_count = match_summary.get('brown_count', 0)
        
        # Приоритет 1: Только зеленые (100%) - без желтых и серых
        if exact_count > 0 and good_count == 0 and brown_count == 0:
            return 1
        
        # Приоритет 2: Зеленые + желтые (100% и 85%+) - может быть и серый тоже
        if exact_count > 0 and good_count > 0:
            return 2
        
        # Приоритет 3: Желтые + серые (85%+ и 56%+) - без зеленых
        # Или только желтые без зеленых и серых
        if exact_count == 0 and good_count > 0:
            if brown_count > 0:
                return 3  # Желтые + серые
            else:
                return 3  # Только желтые
        
        # Приоритет 4: Только серые (56%+) - без зеленых и желтых
        if brown_count > 0 and exact_count == 0 and good_count == 0:
            return 4
        
        # Если ничего не подошло, возвращаем низкий приоритет
        return 999
    
    def set_tenders(self, tenders: List[Dict[str, Any]], total_count: Optional[int] = None):
        """
        Установить/обновить список закупок с синхронизацией карточек.
        
        Единый метод для первичной загрузки и обновления:
        - Создает карточки для новых торгов
        - Обновляет статусы существующих карточек
        - Удаляет карточки торгов, которых нет в новом списке (стали неинтересными или удалены)
        - Сортирует по приоритету
        
        Args:
            tenders: Список торгов из БД (уже отфильтрованный SQL по is_interesting = FALSE)
            total_count: Общее количество торгов в БД (для отображения)
        """
        import time
        start_time = time.time()
        
        # #region agent log
        try:
            log_entry = {
                "sessionId": "debug-session",
                "runId": "perf-1",
                "hypothesisId": "PERF1",
                "location": f"{__file__}:set_tenders:start",
                "message": "Начало set_tenders",
                "data": {
                    "tenders_count": len(tenders),
                    "total_count": total_count,
                },
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception:
            pass
        # #endregion
        
        self.hide_loading()
        
        if not tenders:
            # Если нет торгов - очищаем все карточки
            self.clear_cards()
            # Скрываем счетчик
            if self.count_info:
                self.count_info.hide()
            # Показываем сообщение
            no_data_label = QLabel("Нет новых закупок, соответствующих вашим настройкам")
            apply_label_style(no_data_label, 'info_box_large')
            no_data_label.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(no_data_label)
            return
        
        # Оптимизация: загружаем все match_summary батчем
        batch_load_start = time.time()
        match_summaries_cache = self._load_match_summaries_batch(tenders)
        batch_load_time = time.time() - batch_load_start
        sort_time = 0.0  # Инициализируем для случая, если сортировка не выполнится
        
        # #region agent log
        try:
            log_entry = {
                "sessionId": "debug-session",
                "runId": "perf-1",
                "hypothesisId": "PERF2",
                "location": f"{__file__}:set_tenders:batch_load",
                "message": "Батч-загрузка match_summaries завершена",
                "data": {
                    "batch_load_time_ms": int(batch_load_time * 1000),
                    "cached_count": len(match_summaries_cache),
                },
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception:
            pass
        # #endregion
        
        # Сортируем тендеры по приоритету (используя кэш)
        sort_start = time.time()
        logger.info(f"Синхронизация списка закупок: получено {len(tenders)} торгов")
        sorted_tenders = sorted(tenders, key=lambda t: self._get_tender_priority_cached(t, match_summaries_cache))
        sort_time = time.time() - sort_start
        
        # Создаем словарь существующих карточек по tender_id
        existing_cards = {card.tender_data.get('id'): card for card in self.tender_cards}
        
        # Создаем множество ID торгов из нового списка
        new_tender_ids = {tender.get('id') for tender in sorted_tenders if tender.get('id')}
        
        # #region agent log
        try:
            existing_card_ids = {card.tender_data.get('id') for card in self.tender_cards if card.tender_data.get('id')}
            log_entry = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A",
                "location": f"{__file__}:232",
                "message": "set_tenders: входные данные",
                "data": {
                    "existing_card_ids": list(existing_card_ids),
                    "new_tender_ids": list(new_tender_ids),
                    "existing_count": len(existing_card_ids),
                    "new_count": len(new_tender_ids),
                    "cards_to_remove_ids": list(existing_card_ids - new_tender_ids)
                },
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            pass
        # #endregion
        
        updated_count = 0
        created_count = 0
        removed_count = 0
        
        # Удаляем карточки торгов, которых нет в новом списке
        # (они стали неинтересными или были удалены - SQL уже отфильтровал их)
        cards_to_remove = []
        for card in self.tender_cards:
            tender_id = card.tender_data.get('id')
            if not tender_id:
                continue
            
            # Если торг отсутствует в новом списке - удаляем карточку
            if tender_id not in new_tender_ids:
                # #region agent log
                try:
                    registry_type = card.tender_data.get('registry_type', 'unknown')
                    is_interesting = None
                    if self.tender_match_repository:
                        try:
                            match_result = self.tender_match_repository.get_match_result(tender_id, registry_type)
                            is_interesting = match_result.get('is_interesting') if match_result else None
                        except:
                            pass
                    log_entry = {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B",
                        "location": f"{__file__}:247",
                        "message": "Удаление карточки: торг отсутствует в новом списке",
                        "data": {
                            "tender_id": tender_id,
                            "registry_type": registry_type,
                            "is_interesting_in_db": is_interesting,
                            "will_be_removed": True
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    }
                    with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                except Exception as e:
                    pass
                # #endregion
                cards_to_remove.append(card)
                removed_count += 1
                logger.debug(f"Удаляем карточку торга ID {tender_id} (отсутствует в новом списке - стал неинтересным или удален)")
        
        # Удаляем карточки
        for card in cards_to_remove:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
            if card in self.tender_cards:
                self.tender_cards.remove(card)
            # Удаляем из словаря существующих
            tender_id = card.tender_data.get('id')
            if tender_id in existing_cards:
                del existing_cards[tender_id]
        
        # Обновляем существующие карточки и создаем новые
        for tender in sorted_tenders:
            tender_id = tender.get('id')
            if not tender_id:
                continue
            
            if tender_id in existing_cards:
                # Обновляем существующую карточку
                card = existing_cards[tender_id]
                # Пропускаем, если карточка уже удалена
                if card not in self.tender_cards:
                    continue
                # #region agent log
                try:
                    registry_type = tender.get('registry_type', 'unknown')
                    is_interesting = None
                    if self.tender_match_repository:
                        try:
                            match_result = self.tender_match_repository.get_match_result(tender_id, registry_type)
                            is_interesting = match_result.get('is_interesting') if match_result else None
                        except:
                            pass
                    log_entry = {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "C",
                        "location": f"{__file__}:269",
                        "message": "Обновление существующей карточки",
                        "data": {
                            "tender_id": tender_id,
                            "registry_type": registry_type,
                            "is_interesting_in_db": is_interesting,
                            "will_be_updated": True
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    }
                    with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                except Exception as e:
                    pass
                # #endregion
                try:
                    card.update_status()
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Ошибка при обновлении карточки закупки ID {tender_id}: {e}")
            else:
                # Создаем новую карточку
                try:
                    self.add_tender_card(tender)
                    created_count += 1
                except Exception as e:
                    logger.error(f"Ошибка при создании карточки закупки ID {tender_id}: {e}")
        
        # Обновляем информацию о количестве загруженных закупок (вверху)
        if total_count and total_count > len(sorted_tenders):
            self.count_info.setText(f"Загружено закупок: {len(sorted_tenders)} из {total_count}")
        else:
            self.count_info.setText(f"Загружено закупок: {len(sorted_tenders)}")
        self.count_info.show()
        
        total_time = time.time() - start_time
        
        logger.info(
            f"Синхронизация завершена: обновлено {updated_count}, создано {created_count}, "
            f"удалено {removed_count} карточек. Время: {total_time:.2f}с "
            f"(батч-загрузка: {batch_load_time:.2f}с, сортировка: {sort_time:.2f}с)"
        )
        
        # #region agent log
        try:
            log_entry = {
                "sessionId": "debug-session",
                "runId": "perf-1",
                "hypothesisId": "PERF3",
                "location": f"{__file__}:set_tenders:end",
                "message": "set_tenders завершен",
                "data": {
                    "total_time_ms": int(total_time * 1000),
                    "batch_load_time_ms": int(batch_load_time * 1000),
                    "sort_time_ms": int(sort_time * 1000),
                    "updated_count": updated_count,
                    "created_count": created_count,
                    "removed_count": removed_count,
                },
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception:
            pass
        # #endregion
        
        # #region agent log
        try:
            remaining_card_ids = {card.tender_data.get('id') for card in self.tender_cards if card.tender_data.get('id')}
            log_entry = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "D",
                "location": f"{__file__}:295",
                "message": "set_tenders: результат синхронизации",
                "data": {
                    "remaining_card_ids": list(remaining_card_ids),
                    "remaining_count": len(remaining_card_ids),
                    "updated_count": updated_count,
                    "created_count": created_count,
                    "removed_count": removed_count,
                    "cards_not_in_new_list": list(remaining_card_ids - new_tender_ids)
                },
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            pass
        # #endregion
        
        # Добавляем растягивающийся элемент в конец (если его еще нет)
        if self.cards_layout.count() > 0:
            last_item = self.cards_layout.itemAt(self.cards_layout.count() - 1)
            if last_item and last_item.spacerItem() is None:
                self.cards_layout.addStretch()
    
    def _on_card_selection_changed(self, selected: bool):
        """Обработка изменения выбора карточки"""
        # Передаем сигнал наверх в BidsWidget
        if hasattr(self.parent(), 'on_tender_selection_changed'):
            self.parent().on_tender_selection_changed()
    
    def get_selected_tenders(self) -> List[Dict[str, Any]]:
        """Получить список выбранных закупок"""
        selected = []
        for card in self.tender_cards:
            if hasattr(card, 'is_selected') and card.is_selected:
                selected.append(card.tender_data)
        return selected
    
    def update_tenders(self, tenders: List[Dict[str, Any]], total_count: Optional[int] = None):
        """
        Обновить список закупок (обертка над set_tenders для обратной совместимости).
        
        Теперь set_tenders и update_tenders делают одно и то же - синхронизацию списка.
        SQL уже отфильтровал неинтересные торги (is_interesting = FALSE),
        поэтому мы просто синхронизируем UI с новым списком.
        """
        self.set_tenders(tenders, total_count)

