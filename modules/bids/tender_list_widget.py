"""
Виджет списка карточек торгов с индикатором загрузки
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame, QLabel
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from typing import List, Dict, Any, Callable, Optional

from modules.bids.tender_card import TenderCard
from modules.styles.general_styles import COLORS, FONT_SIZES, SIZES, apply_label_style
from services.document_search_service import DocumentSearchService


class TenderListWidget(QWidget):
    """
    Виджет списка карточек торгов с прокруткой и индикатором загрузки
    """
    
    def __init__(
        self,
        parent=None,
        document_search_service: Optional[DocumentSearchService] = None,
    ):
        super().__init__(parent)
        self.tender_cards: List[TenderCard] = []
        self.document_search_service = document_search_service
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
        loading_label = QLabel("⏳ Загрузка торгов...")
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
        """Очистить все карточки"""
        for card in self.tender_cards:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self.tender_cards.clear()
    
    def add_tender_card(self, tender_data: Dict[str, Any]):
        """Добавить карточку торга"""
        try:
            card = TenderCard(
                tender_data,
                document_search_service=self.document_search_service,
                parent=self,
            )
            self.tender_cards.append(card)
            self.cards_layout.addWidget(card)
        except Exception as e:
            from loguru import logger
            logger.error(f"Ошибка при создании карточки торга: {e}")
            logger.error(f"Данные торга: {tender_data.get('id', 'нет ID')}")
    
    def set_tenders(self, tenders: List[Dict[str, Any]], total_count: Optional[int] = None):
        """Установить список торгов"""
        self.clear_cards()
        self.hide_loading()
        
        if not tenders:
            # Показываем сообщение, если нет торгов
            no_data_label = QLabel("Нет новых торгов, соответствующих вашим настройкам")
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
        
        # Добавляем информацию о количестве загруженных торгов
        count_info = QLabel(f"Загружено торгов: {len(tenders)}")
        if total_count and total_count > len(tenders):
            count_info.setText(f"Загружено торгов: {len(tenders)} из {total_count}")
        apply_label_style(count_info, 'small')
        count_info.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_light']};
                padding: 10px 15px;
                background: {COLORS['white']};
                border-radius: {SIZES['border_radius_normal']}px;
                margin-bottom: 10px;
            }}
        """)
        self.cards_layout.addWidget(count_info)
        
        from loguru import logger
        logger.info(f"Начинаем добавление {len(tenders)} карточек торгов в виджет")
        
        added_count = 0
        for tender in tenders:
            try:
                self.add_tender_card(tender)
                added_count += 1
            except Exception as e:
                logger.error(f"Ошибка при добавлении карточки торга ID {tender.get('id', 'неизвестно')}: {e}")
        
        logger.info(f"Добавлено карточек торгов: {added_count} из {len(tenders)}")
        
        # Добавляем растягивающийся элемент в конец
        self.cards_layout.addStretch()

