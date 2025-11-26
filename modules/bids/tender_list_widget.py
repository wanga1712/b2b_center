"""
Виджет списка карточек закупок с индикатором загрузки
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame, QLabel
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from typing import List, Dict, Any, Callable, Optional

from modules.bids.tender_card import TenderCard
from modules.styles.general_styles import COLORS, FONT_SIZES, SIZES, apply_label_style
from services.document_search_service import DocumentSearchService
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.tender_match_repository import TenderMatchRepository


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
        self.count_info: Optional[QLabel] = None  # Ссылка на виджет с информацией о количестве
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Прокручиваемая область
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: {COLORS['secondary']};
            }}
        """)
        
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
        frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['white']};
                border-radius: {SIZES['border_radius_normal']}px;
                padding: 30px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignCenter)
        
        # Анимированный текст (можно заменить на QProgressBar или QMovie)
        loading_label = QLabel("⏳ Загрузка закупок...")
        apply_label_style(loading_label, 'h2')
        loading_label.setStyleSheet(f"color: {COLORS['primary']};")
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
        """Очистить все карточки и информацию о количестве"""
        for card in self.tender_cards:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self.tender_cards.clear()
        
        # Удаляем информацию о количестве, если она существует
        if self.count_info:
            self.cards_layout.removeWidget(self.count_info)
            self.count_info.deleteLater()
            self.count_info = None
    
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
            from loguru import logger
            logger.error(f"Ошибка при создании карточки закупки: {e}")
            logger.error(f"Данные закупки: {tender_data.get('id', 'нет ID')}")
    
    def set_tenders(self, tenders: List[Dict[str, Any]], total_count: Optional[int] = None):
        """Установить список закупок (полная перезагрузка)"""
        self.clear_cards()
        self.hide_loading()
        
        if not tenders:
            # Показываем сообщение, если нет закупок
            no_data_label = QLabel("Нет новых закупок, соответствующих вашим настройкам")
            apply_label_style(no_data_label, 'normal')
            no_data_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['text_light']};
                    font-style: italic;
                    padding: 30px;
                    background: {COLORS['white']};
                    border-radius: {SIZES['border_radius_normal']}px;
                }}
            """)
            no_data_label.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(no_data_label)
            return
        
        # Добавляем или обновляем информацию о количестве загруженных закупок
        if not self.count_info:
            self.count_info = QLabel()
            apply_label_style(self.count_info, 'small')
            self.count_info.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['text_light']};
                    padding: 10px 15px;
                    background: {COLORS['white']};
                    border-radius: {SIZES['border_radius_normal']}px;
                    margin-bottom: 10px;
                }}
            """)
            self.cards_layout.addWidget(self.count_info)
        
        # Обновляем текст
        if total_count and total_count > len(tenders):
            self.count_info.setText(f"Загружено закупок: {len(tenders)} из {total_count}")
        else:
            self.count_info.setText(f"Загружено закупок: {len(tenders)}")
        
        from loguru import logger
        logger.info(f"Начинаем добавление {len(tenders)} карточек закупок в виджет")
        
        added_count = 0
        for tender in tenders:
            try:
                self.add_tender_card(tender)
                added_count += 1
            except Exception as e:
                logger.error(f"Ошибка при добавлении карточки закупки ID {tender.get('id', 'неизвестно')}: {e}")
        
        logger.info(f"Добавлено карточек закупок: {added_count} из {len(tenders)}")
        
        # Добавляем растягивающийся элемент в конец
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
        Обновить список закупок (обновление статусов существующих карточек)
        
        Если карточка уже существует - обновляем её статус
        Если карточки нет - создаем новую
        """
        from loguru import logger
        
        # Создаем словарь существующих карточек по tender_id
        existing_cards = {card.tender_data.get('id'): card for card in self.tender_cards}
        
        updated_count = 0
        created_count = 0
        
        for tender in tenders:
            tender_id = tender.get('id')
            if not tender_id:
                continue
            
            if tender_id in existing_cards:
                # Обновляем существующую карточку
                card = existing_cards[tender_id]
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
        
        logger.info(f"Обновлено карточек: {updated_count}, создано новых: {created_count}")
        
        self.hide_loading()

