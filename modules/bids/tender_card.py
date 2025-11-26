"""
Виджет карточки закупки (сокращенный и полный вид)

Карточка отображает информацию о закупке:
- Сокращенный вид: основная информация
- Полный вид: вся информация при двойном клике
"""

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog,
    QScrollArea, QWidget, QTextEdit, QMessageBox, QApplication, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QThread
from PyQt5.QtGui import QFont, QDesktopServices
from PyQt5.QtWidgets import QDesktopWidget
from typing import Dict, Any, Optional, TYPE_CHECKING, List
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from modules.styles.general_styles import (
    COLORS, FONT_SIZES, SIZES, apply_label_style, apply_button_style,
    apply_text_style_light, apply_text_style_primary, apply_font_weight
)
from core.exceptions import DocumentSearchError
from config.settings import config
from services.document_search.document_downloader import DocumentDownloader


def _build_link_label(text: str, url: str) -> QLabel:
    """Создает кликабельную текстовую ссылку."""
    link_label = QLabel(f'<a href="{url}">{text}</a>')
    apply_label_style(link_label, 'small')
    link_label.setTextFormat(Qt.RichText)
    link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
    link_label.setOpenExternalLinks(True)
    return link_label


def _format_balance_holder(data: Dict[str, Any]) -> Optional[str]:
    """Форматирует подпись балансодержателя."""
    name = data.get('balance_holder_name')
    inn = data.get('balance_holder_inn')
    if name and inn:
        return f"{name} (ИНН {inn})"
    return name or None

if TYPE_CHECKING:
    from services.document_search_service import DocumentSearchService
    from services.tender_match_repository import TenderMatchRepository


class TenderCard(QFrame):
    MATCH_DETAILS_CACHE_LIMIT = 20
    selection_changed = pyqtSignal(bool)  # Сигнал изменения выбора
    
    """
    Карточка закупки (сокращенный вид)
    
    Отображает основную информацию о закупке.
    При двойном клике открывается диалог с полной информацией.
    """
    
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
        self.is_selected = False  # Флаг выбора закупки
        try:
            self.init_ui()
        except Exception as e:
            from loguru import logger
            logger.error(f"Ошибка при инициализации карточки закупки ID {tender_data.get('id', 'неизвестно')}: {e}")
            raise
    
    def init_ui(self):
        """Инициализация интерфейса карточки"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Стиль карточки
        self.setStyleSheet(f"""
            TenderCard {{
                background: {COLORS['white']};
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
                min-height: 120px;
            }}
            TenderCard:hover {{
                border: 2px solid {COLORS['primary']};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }}
        """)
        
        # Верхняя строка: звездочка выбора и название закупки
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # Звездочка для выбора закупки
        self.select_checkbox = QCheckBox()
        self.select_checkbox.setStyleSheet(f"""
            QCheckBox {{
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 24px;
                height: 24px;
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                background: {COLORS['white']};
            }}
            QCheckBox::indicator:checked {{
                background: {COLORS['primary']};
                border: 2px solid {COLORS['primary']};
            }}
            QCheckBox::indicator:checked::after {{
                content: "★";
                color: {COLORS['white']};
                font-size: 16px;
            }}
        """)
        self.select_checkbox.stateChanged.connect(self._on_selection_changed)
        header_layout.addWidget(self.select_checkbox)
        
        # Название закупки
        purchase_name = self.tender_data.get('auction_name', 'Без названия')
        name_label = QLabel(purchase_name)
        apply_label_style(name_label, 'h3')
        name_label.setWordWrap(True)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_dark']};
                font-weight: bold;
                margin-bottom: 5px;
            }}
        """)
        header_layout.addWidget(name_label, 1)
        
        layout.addLayout(header_layout)
        
        # Информация в одну строку
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)
        
        # Номер контракта
        contract_number = self.tender_data.get('contract_number', '')
        if contract_number:
            contract_label = QLabel(f"№ {contract_number}")
            apply_label_style(contract_label, 'small')
            apply_text_style_light(contract_label)
            info_layout.addWidget(contract_label)
        
        # Регион
        region_name = self.tender_data.get('region_name') or self.tender_data.get('delivery_region', '')
        if region_name:
            region_label = QLabel(f"📍 {region_name}")
            apply_label_style(region_label, 'small')
            apply_text_style_light(region_label)
            info_layout.addWidget(region_label)
        
        # Заказчик
        customer_name = (
            self.tender_data.get('customer_short_name') or 
            self.tender_data.get('customer_full_name', '')
        )
        if customer_name:
            customer_label = QLabel(f"👤 {customer_name[:50]}")
            apply_label_style(customer_label, 'small')
            apply_text_style_light(customer_label)
            customer_label.setToolTip(customer_name)
            info_layout.addWidget(customer_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Цена и даты
        price_date_layout = QHBoxLayout()
        price_date_layout.setSpacing(15)
        
        # Начальная цена
        initial_price = self.tender_data.get('initial_price')
        if initial_price:
            price_str = f"{float(initial_price):,.0f}".replace(',', ' ')
            price_label = QLabel(f"💰 {price_str} ₽")
            apply_label_style(price_label, 'normal')
            apply_text_style_primary(price_label)
            apply_font_weight(price_label)
            price_date_layout.addWidget(price_label)
        
        # Дата окончания
        end_date = self.tender_data.get('end_date')
        if end_date:
            if isinstance(end_date, str):
                try:
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                except:
                    pass
            if hasattr(end_date, 'strftime'):
                date_str = end_date.strftime('%d.%m.%Y')
                date_label = QLabel(f"📅 До {date_str}")
                apply_label_style(date_label, 'small')
                apply_text_style_light(date_label)
                price_date_layout.addWidget(date_label)
        
        price_date_layout.addStretch()
        layout.addLayout(price_date_layout)
        
        # Дополнительные атрибуты: площадка, балансодержатель, ссылка
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(15)
        meta_items = 0
        
        platform_name = self.tender_data.get('platform_name')
        if platform_name:
            platform_label = QLabel(f"🏛 {platform_name}")
            apply_label_style(platform_label, 'small')
            apply_text_style_light(platform_label)
            meta_layout.addWidget(platform_label)
            meta_items += 1
        
        balance_holder_text = _format_balance_holder(self.tender_data)
        if balance_holder_text:
            balance_label = QLabel(f"🏢 {balance_holder_text}")
            apply_label_style(balance_label, 'small')
            apply_text_style_light(balance_label)
            meta_layout.addWidget(balance_label)
            meta_items += 1
        
        tender_link = self.tender_data.get('tender_link')
        if tender_link:
            link_label = _build_link_label("Ссылка на закупку", tender_link)
            meta_layout.addWidget(link_label)
            meta_items += 1
        
        if meta_items:
            meta_layout.addStretch()
            layout.addLayout(meta_layout)
        
        # ОКПД код
        okpd_code = (
            self.tender_data.get('okpd_sub_code') or 
            self.tender_data.get('okpd_main_code', '')
        )
        if okpd_code:
            okpd_label = QLabel(f"ОКПД: {okpd_code}")
            apply_label_style(okpd_label, 'small')
            apply_text_style_light(okpd_label)
            layout.addWidget(okpd_label)
        
        # Значки статуса обработки и совпадений
        status_layout = QHBoxLayout()
        status_layout.setSpacing(10)
        self.status_container = self._create_status_badges()
        if self.status_container:
            status_layout.addWidget(self.status_container)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        self.matches_preview = self._create_matches_preview()
        if self.matches_preview:
            layout.addWidget(self.matches_preview)
        
        # Включаем обработку двойного клика
        self.setMouseTracking(True)
    
    def mouseDoubleClickEvent(self, event):
        """Обработка двойного клика - открытие полной информации"""
        super().mouseDoubleClickEvent(event)
        dialog = TenderDetailDialog(
            self.tender_data,
            document_search_service=self.document_search_service,
            tender_match_repository=self.tender_match_repository,
            registry_type=self._registry_type,
            initial_match_summary=self._match_summary_cache,
            initial_match_details=self._match_details_cache,
            parent=self,
        )
        dialog.exec_()
    
    def _create_status_badges(self) -> Optional[QWidget]:
        """
        Создание значков статуса обработки и совпадений
        
        Логика отображения:
        - Если найдены 100% совпадения - показываем зеленый значок
        - Если найдены 85% совпадения - показываем желтый значок (даже если есть 100%)
        - Если ничего не найдено (0 совпадений) - красный значок
        - Если не обработано - красный значок "Не обработано"
        """
        tender_id = self.tender_data.get('id')
        if not tender_id:
            logger.warning("⚠️ [TenderCard._create_status_badges] tender_id отсутствует в данных закупки")
            return None
        
        summary = self._fetch_match_summary()
        
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setSpacing(8)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        if not summary:
            # Документы не обработаны - красный значок
            logger.info(f"🔴 [TenderCard._create_status_badges] Закупка {tender_id} не обработана - показываем красный значок")
            badge = self._create_badge("🔴 Не обработано", "#dc3545", "#fff3cd", "Документы не обработаны")
            container_layout.addWidget(badge)
            return container
        
        match_result = summary.get('match_result', {})
        exact_count = summary.get('exact_count', 0)
        good_count = summary.get('good_count', 0)
        total_count = summary.get('total_count', 0) or match_result.get('match_count', 0)
        
        logger.info(f"📈 [TenderCard._create_status_badges] Статистика для закупки {tender_id}: "
                   f"exact_count={exact_count}, good_count={good_count}, total_count={total_count}")
        logger.info(f"📋 [TenderCard._create_status_badges] match_result: {match_result}")
        
        # Если есть 100% совпадения - показываем зеленый значок
        if exact_count > 0:
            logger.info(f"🟢 [TenderCard._create_status_badges] Найдено {exact_count} совпадений 100% - показываем зеленый значок")
            badge = self._create_badge(
                f"🟢 {exact_count} совпадений",
                "#28a745",
                "#d4edda",
                f"100% совпадений. Найдено товаров: {exact_count}"
            )
            container_layout.addWidget(badge)
        
        # Если есть 85% совпадения - показываем желтый значок
        if good_count > 0:
            logger.info(f"🟡 [TenderCard._create_status_badges] Найдено {good_count} совпадений 85% - показываем желтый значок")
            badge = self._create_badge(
                f"🟡 {good_count} совпадений",
                "#ffc107",
                "#fff3cd",
                f"85% совпадений. Найдено товаров: {good_count}"
            )
            container_layout.addWidget(badge)
        
        # Если нет совпадений (0) - показываем красный значок
        if exact_count == 0 and good_count == 0 and total_count == 0:
            logger.info(f"🔴 [TenderCard._create_status_badges] Совпадений не найдено - показываем красный значок")
            badge = self._create_badge(
                "🔴 0 совпадений",
                "#dc3545",
                "#f8d7da",
                "Совпадений не найдено"
            )
            container_layout.addWidget(badge)
        
        logger.info(f"✅ [TenderCard._create_status_badges] Карточка для закупки {tender_id} сформирована")
        return container
    
    def _create_matches_preview(self) -> Optional[QWidget]:
        """Создает небольшую секцию с найденными товарами из документов."""
        summary = self._fetch_match_summary()
        if not summary:
            return None
        
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['secondary']};
                border-radius: {SIZES['border_radius_small']}px;
                padding: 8px 12px;
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Совпадения по документам")
        apply_label_style(title, 'normal')
        apply_font_weight(title)
        layout.addWidget(title)
        
        stats_label = QLabel(
            f"100%: {summary.get('exact_count', 0)} • "
            f"85%: {summary.get('good_count', 0)} • "
            f"Всего: {summary.get('total_count', 0)}"
        )
        apply_label_style(stats_label, 'small')
        apply_text_style_light(stats_label)
        layout.addWidget(stats_label)
        
        details = self._fetch_match_details(limit=3)
        if details:
            for detail in details:
                product_name = detail.get('product_name') or "Без названия"
                score = detail.get('score') or 0
                sheet = detail.get('sheet_name') or "лист"
                cell = detail.get('cell_address') or ""
                item_label = QLabel(f"• {product_name} — {score:.0f}% ({sheet} {cell})")
                apply_label_style(item_label, 'small')
                layout.addWidget(item_label)
        else:
            empty_label = QLabel("Документы обработаны, но совпадения не найдены.")
            apply_label_style(empty_label, 'small')
            layout.addWidget(empty_label)
        
        return container
    
    def _create_badge(self, text: str, text_color: str, background_color: str, tooltip: str) -> QLabel:
        """Создание значка статуса"""
        badge = QLabel(text)
        badge.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-weight: bold;
                font-size: 12px;
                padding: 4px 8px;
                background: {background_color};
                border-radius: 4px;
            }}
        """)
        badge.setToolTip(tooltip)
        return badge
    
    def _fetch_match_summary(self) -> Optional[Dict[str, Any]]:
        """Получение сводки совпадений с кэшем."""
        if not self.tender_match_repository:
            return None
        if self._match_summary_cache is None:
            tender_id = self.tender_data.get('id')
            if not tender_id:
                return None
            self._match_summary_cache = self.tender_match_repository.get_match_summary(
                tender_id,
                self._registry_type,
            )
        return self._match_summary_cache
    
    def _fetch_match_details(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получение детальных совпадений с кэшем."""
        if not self.tender_match_repository:
            return []
        if self._match_details_cache is None:
            tender_id = self.tender_data.get('id')
            if not tender_id:
                return []
            summary = self._fetch_match_summary()
            if not summary:
                self._match_details_cache = []
            else:
                self._match_details_cache = self.tender_match_repository.get_match_details(
                    tender_id,
                    self._registry_type,
                    limit=self.MATCH_DETAILS_CACHE_LIMIT,
                )
        details = self._match_details_cache or []
        if limit:
            return details[:limit]
        return details
    
    def update_status(self):
        """Обновление статуса карточки без пересоздания"""
        self._match_summary_cache = None
        self._match_details_cache = None
        # Удаляем старый контейнер
        if self.status_container:
            if self.status_container.parent():
                parent_layout = self.status_container.parent().layout()
                if parent_layout:
                    parent_layout.removeWidget(self.status_container)
            self.status_container.deleteLater()
            self.status_container = None
        if self.matches_preview:
            layout = self.layout()
            if layout:
                layout.removeWidget(self.matches_preview)
            self.matches_preview.deleteLater()
            self.matches_preview = None
        
        # Создаем новый контейнер
        self.status_container = self._create_status_badges()
        if self.status_container:
            # Находим layout статуса и добавляем новый контейнер
            main_layout = self.layout()
            for i in range(main_layout.count()):
                item = main_layout.itemAt(i)
                if item and item.layout():
                    layout = item.layout()
                    # Проверяем, что это QHBoxLayout статуса (содержит stretch в конце)
                    if isinstance(layout, QHBoxLayout) and layout.count() > 0:
                        last_item = layout.itemAt(layout.count() - 1)
                        if last_item and last_item.spacerItem():
                            # Это layout статуса - вставляем новый контейнер в начало
                            layout.insertWidget(0, self.status_container)
                            break
        self.matches_preview = self._create_matches_preview()
        if self.matches_preview:
            self.layout().addWidget(self.matches_preview)
    
    def _on_selection_changed(self, state: int):
        """Обработка изменения выбора закупки"""
        self.is_selected = (state == Qt.Checked)
        self.selection_changed.emit(self.is_selected)
    
    def set_selected(self, selected: bool):
        """Установить состояние выбора закупки"""
        if hasattr(self, 'select_checkbox'):
            self.select_checkbox.setChecked(selected)
            self.is_selected = selected
    
    def _determine_registry_type(self) -> str:
        """Определяет тип реестра (44ФЗ/223ФЗ) для именования папок."""
        raw_value = (
            self.tender_data.get('registry_type')
            or self.tender_data.get('law')
            or ''
        )
        value = str(raw_value).lower()
        if '223' in value:
            return '223fz'
        return '44fz'
    
class TenderDetailDialog(QDialog):
    """
    Диалог с полной информацией о закупке
    """
    
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
        self.tender_data = tender_data
        self.document_search_service = document_search_service
        self.tender_match_repository = tender_match_repository
        self.registry_type = registry_type or self._determine_registry_type()
        self.match_summary = initial_match_summary
        self.match_details = initial_match_details
        
        # Настройка диалога в полном размере (аналог Bitrix)
        self.setWindowTitle("Подробная информация о закупке")
        self._set_fullscreen_size()
        self._load_match_data()
        
        self.init_ui()
    
    def _set_fullscreen_size(self):
        """Установка размера диалога в полный размер экрана (95% от доступной области)"""
        screen = QApplication.primaryScreen()
        if screen:
            available_geometry = screen.availableGeometry()
            # Используем 95% от доступной области для безопасного отступа
            width = int(available_geometry.width() * 0.95)
            height = int(available_geometry.height() * 0.95)
            self.resize(width, height)
            # Центрируем диалог
            x = available_geometry.x() + (available_geometry.width() - width) // 2
            y = available_geometry.y() + (available_geometry.height() - height) // 2
            self.move(x, y)
        else:
            # Fallback на стандартный размер
            from modules.styles.ui_config import configure_dialog
            configure_dialog(self, "Подробная информация о закупке", size_preset="tender_detail")
    
    def _determine_registry_type(self) -> str:
        raw_value = (
            self.tender_data.get('registry_type')
            or self.tender_data.get('law')
            or ''
        )
        value = str(raw_value).lower()
        if '223' in value:
            return '223fz'
        return '44fz'
    
    def _load_match_data(self):
        """Подгружает сводку и детали совпадений, если есть репозиторий."""
        if not self.tender_match_repository:
            if self.match_summary is None:
                self.match_summary = None
            if self.match_details is None:
                self.match_details = []
            return
        
        tender_id = self.tender_data.get('id')
        if not tender_id:
            self.match_summary = None
            self.match_details = []
            return
        
        if self.match_summary is None:
            self.match_summary = self.tender_match_repository.get_match_summary(
                tender_id,
                self.registry_type,
            )
        if self.match_details is None:
            self.match_details = self.tender_match_repository.get_match_details(
                tender_id,
                self.registry_type,
                limit=20,
            )
    
    def init_ui(self):
        """Инициализация интерфейса диалога"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Прокручиваемая область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_normal']}px;
                background: {COLORS['white']};
            }}
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        purchase_name = self.tender_data.get('auction_name', 'Без названия')
        name_label = QLabel(purchase_name)
        apply_label_style(name_label, 'h1')
        name_label.setWordWrap(True)
        content_layout.addWidget(name_label)
        content_layout.addWidget(self._create_separator())
        
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(15)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(12)
        
        left_layout.addWidget(self._create_info_section("Основная информация", [
            ("Номер контракта", self.tender_data.get('contract_number')),
            ("Площадка", self.tender_data.get('platform_name')),
            ("Балансодержатель", _format_balance_holder(self.tender_data)),
            ("Регион", self.tender_data.get('region_name') or self.tender_data.get('delivery_region')),
        ]))
        
        left_layout.addWidget(self._create_info_section("Участники", [
            ("Заказчик", self.tender_data.get('customer_full_name') or self.tender_data.get('customer_short_name')),
            ("Подрядчик", self.tender_data.get('contractor_full_name') or self.tender_data.get('contractor_short_name')),
        ]))
        
        okpd_code = (
            self.tender_data.get('okpd_sub_code') or 
            self.tender_data.get('okpd_main_code', '')
        )
        okpd_name = self.tender_data.get('okpd_name', '')
        if okpd_code:
            left_layout.addWidget(self._create_info_section("ОКПД", [
                ("Код", okpd_code),
                ("Название", okpd_name),
            ]))
        
        left_layout.addWidget(self._create_info_section("Финансы", [
            ("Начальная цена", self._format_price(self.tender_data.get('initial_price'))),
            ("Финальная цена", self._format_price(self.tender_data.get('final_price'))),
            ("Сумма обеспечения", self._format_price(self.tender_data.get('guarantee_amount'))),
        ]))
        
        left_layout.addWidget(self._create_info_section("Даты", [
            ("Дата начала", self._format_date(self.tender_data.get('start_date'))),
            ("Дата окончания", self._format_date(self.tender_data.get('end_date'))),
            ("Начало поставки", self._format_date(self.tender_data.get('delivery_start_date'))),
            ("Конец поставки", self._format_date(self.tender_data.get('delivery_end_date'))),
        ]))
        
        delivery_region = self.tender_data.get('delivery_region')
        delivery_address = self.tender_data.get('delivery_address')
        if delivery_region or delivery_address:
            left_layout.addWidget(self._create_info_section("Доставка", [
                ("Регион доставки", delivery_region),
                ("Адрес доставки", delivery_address),
            ]))
        
        document_links = self.tender_data.get('document_links', [])
        if document_links:
            left_layout.addWidget(self._create_documents_section(document_links))
        
        tender_link = self.tender_data.get('tender_link')
        if tender_link:
            left_layout.addWidget(_build_link_label("Ссылка на закупку", tender_link))
        
        left_layout.addStretch()
        columns_layout.addWidget(left_widget, 2)
        
        match_column = self._create_match_column()
        if match_column:
            columns_layout.addWidget(match_column, 1)
        
        content_layout.addLayout(columns_layout)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Кнопка закрытия
        btn_close = QPushButton("Закрыть")
        apply_button_style(btn_close, 'secondary')
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
    
    def _create_separator(self) -> QFrame:
        """Создание разделителя"""
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"color: {COLORS['border']};")
        return separator
    
    def _create_info_section(self, title: str, items: list) -> QWidget:
        """Создание секции с информацией"""
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['secondary']};
                border-radius: {SIZES['border_radius_normal']}px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(section)
        layout.setSpacing(8)
        
        # Заголовок секции
        title_label = QLabel(title)
        apply_label_style(title_label, 'h2')
        layout.addWidget(title_label)
        
        # Элементы
        for label, value in items:
            if value:
                item_layout = QHBoxLayout()
                label_widget = QLabel(f"{label}:")
                apply_label_style(label_widget, 'normal')
                apply_text_style_light(label_widget)
                label_widget.setStyleSheet(label_widget.styleSheet() + " min-width: 150px;")
                item_layout.addWidget(label_widget)
                
                value_widget = QLabel(str(value))
                value_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
                apply_label_style(value_widget, 'normal')
                value_widget.setWordWrap(True)
                item_layout.addWidget(value_widget)
                layout.addLayout(item_layout)
        
        return section
    
    def _create_documents_section(self, document_links: list) -> QWidget:
        """Создание секции со ссылками на документы"""
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['secondary']};
                border-radius: {SIZES['border_radius_normal']}px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(section)
        layout.setSpacing(8)
        
        # Заголовок и кнопка скачивания
        header_layout = QHBoxLayout()
        title_label = QLabel("Документы")
        apply_label_style(title_label, 'h2')
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Кнопка скачивания всех документов
        if document_links:
            btn_download_all = QPushButton("⬇️ Скачать все документы")
            apply_button_style(btn_download_all, 'primary')
            btn_download_all.clicked.connect(lambda: self._handle_download_all_documents(document_links))
            header_layout.addWidget(btn_download_all)
        
        layout.addLayout(header_layout)
        
        for doc in document_links:
            doc_link = doc.get('document_links', '')
            file_name = doc.get('file_name', 'Документ')
            if doc_link:
                btn_doc = QPushButton(f"📄 {file_name}")
                apply_button_style(btn_doc, 'outline')
                btn_doc.clicked.connect(lambda checked, link=doc_link: QDesktopServices.openUrl(QUrl(link)))
                layout.addWidget(btn_doc)
        
        return section
    
    def _create_match_column(self) -> Optional[QWidget]:
        """Создает правую колонку с результатами поиска по документам."""
        if not self.match_summary and not self.match_details:
            return None
        
        column = QFrame()
        column.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['secondary']};
                border-radius: {SIZES['border_radius_normal']}px;
                padding: 12px;
            }}
        """)
        layout = QVBoxLayout(column)
        layout.setSpacing(12)
        layout.addWidget(self._create_match_summary_block())
        layout.addWidget(self._create_match_details_block())
        layout.addStretch()
        return column
    
    def _create_match_summary_block(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: transparent; }")
        layout = QVBoxLayout(frame)
        layout.setSpacing(6)
        
        title = QLabel("Результаты анализа документов")
        apply_label_style(title, 'h2')
        layout.addWidget(title)
        
        if not self.match_summary:
            empty_label = QLabel("Документы по закупке ещё не обработаны.")
            apply_label_style(empty_label, 'normal')
            apply_text_style_light(empty_label)
            layout.addWidget(empty_label)
            return frame
        
        summary_text = QLabel(
            f"100% совпадения: {self.match_summary.get('exact_count', 0)}\n"
            f"85% совпадения: {self.match_summary.get('good_count', 0)}\n"
            f"Всего совпадений: {self.match_summary.get('total_count', 0)}"
        )
        apply_label_style(summary_text, 'normal')
        layout.addWidget(summary_text)
        return frame
    
    def _create_match_details_block(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: transparent; }")
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        
        title = QLabel("Найденные товары")
        apply_label_style(title, 'h2')
        layout.addWidget(title)
        
        details = self.match_details or []
        if not details:
            empty_label = QLabel("Совпадения ещё не обнаружены.")
            apply_label_style(empty_label, 'normal')
            apply_text_style_light(empty_label)
            layout.addWidget(empty_label)
            return frame
        
        for detail in details:
            layout.addWidget(self._create_match_detail_card(detail))
        
        return frame
    
    def _create_match_detail_card(self, detail: Dict[str, Any]) -> QWidget:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['white']};
                border-radius: {SIZES['border_radius_small']}px;
                padding: 8px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        
        product_name = detail.get('product_name') or "Без названия"
        score = detail.get('score') or 0
        header = QLabel(f"{product_name} — {score:.0f}%")
        apply_label_style(header, 'normal')
        apply_font_weight(header)
        layout.addWidget(header)
        
        sheet = detail.get('sheet_name') or "лист"
        cell = detail.get('cell_address') or ""
        location = QLabel(f"{sheet} {cell}".strip())
        apply_label_style(location, 'small')
        apply_text_style_light(location)
        layout.addWidget(location)
        
        source = detail.get('source_file')
        if source:
            source_label = QLabel(f"Файл: {source}")
            apply_label_style(source_label, 'small')
            layout.addWidget(source_label)
        
        snippet = detail.get('matched_display_text') or detail.get('matched_text')
        if snippet:
            snippet_label = QLabel(f"Фрагмент: {snippet}")
            snippet_label.setWordWrap(True)
            apply_label_style(snippet_label, 'small')
            layout.addWidget(snippet_label)
        
        return card
    
    def _format_price(self, price: Optional[Any]) -> str:
        """Форматирование цены"""
        if not price:
            return "—"
        try:
            return f"{float(price):,.0f} ₽".replace(',', ' ')
        except:
            return str(price)
    
    def _format_date(self, date_value: Optional[Any]) -> str:
        """Форматирование даты"""
        if not date_value:
            return "—"
        try:
            if isinstance(date_value, str):
                date_value = datetime.strptime(date_value, '%Y-%m-%d').date()
            if hasattr(date_value, 'strftime'):
                return date_value.strftime('%d.%m.%Y')
            return str(date_value)
        except:
            return str(date_value) if date_value else "—"
    
    def _handle_download_all_documents(self, document_links: list):
        """Обработчик нажатия кнопки скачивания всех документов"""
        if not document_links:
            QMessageBox.warning(self, "Предупреждение", "Нет документов для скачивания")
            return
        
        # Получаем путь из конфигурации
        download_dir = Path(config.document_download_dir) if config.document_download_dir else None
        if not download_dir:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не настроен путь для скачивания документов.\n"
                "Установите переменную DOCUMENT_DOWNLOAD_DIR в .env файле."
            )
            return
        
        # Создаем поток для скачивания
        download_thread = DocumentDownloadThread(document_links, download_dir, self.tender_data)
        download_thread.progress_updated.connect(self._on_download_progress)
        download_thread.finished.connect(self._on_download_finished)
        download_thread.error_occurred.connect(self._on_download_error)
        download_thread.start()
        
        # Показываем сообщение о начале скачивания
        QMessageBox.information(
            self,
            "Скачивание документов",
            f"Начато скачивание {len(document_links)} документов.\n"
            f"Файлы будут сохранены в: {download_dir}"
        )
    
    def _on_download_progress(self, current: int, total: int, file_name: str):
        """Обработчик обновления прогресса скачивания"""
        logger.info(f"Скачивание: {current}/{total} - {file_name}")
    
    def _on_download_finished(self, downloaded_count: int, total_count: int, download_dir: Path):
        """Обработчик завершения скачивания"""
        QMessageBox.information(
            self,
            "Скачивание завершено",
            f"Скачано документов: {downloaded_count} из {total_count}\n"
            f"Файлы сохранены в: {download_dir}"
        )
    
    def _on_download_error(self, error_message: str):
        """Обработчик ошибки при скачивании"""
        QMessageBox.warning(self, "Ошибка скачивания", error_message)


class DocumentDownloadThread(QThread):
    """Поток для асинхронного скачивания документов"""
    
    progress_updated = pyqtSignal(int, int, str)  # current, total, file_name
    finished = pyqtSignal(int, int, Path)  # downloaded_count, total_count, download_dir
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, document_links: List[Dict[str, Any]], download_dir: Path, tender_data: Dict[str, Any]):
        super().__init__()
        self.document_links = document_links
        self.download_dir = download_dir
        self.tender_data = tender_data
    
    def run(self):
        """Выполнение скачивания документов"""
        try:
            # Определяем тип реестра
            registry_type = self._determine_registry_type()
            tender_id = self.tender_data.get('id')
            
            # Создаем папку для закупки
            if tender_id:
                folder_name = f"{registry_type}_{tender_id}"
            else:
                folder_name = "tender_temp"
            
            tender_folder = self.download_dir / folder_name
            tender_folder.mkdir(parents=True, exist_ok=True)
            
            # Инициализируем загрузчик
            downloader = DocumentDownloader(tender_folder)
            
            total_docs = len(self.document_links)
            downloaded_count = 0
            batch_size = 8
            
            # Скачиваем документы по 8 штук за раз (параллельно внутри батча)
            for start_idx in range(0, total_docs, batch_size):
                end_idx = min(start_idx + batch_size, total_docs)
                batch = self.document_links[start_idx:end_idx]
                
                logger.info(f"Скачивание документов {start_idx + 1}-{end_idx} из {total_docs} (параллельно)")
                
                # Параллельное скачивание документов в батче
                with ThreadPoolExecutor(max_workers=min(batch_size, len(batch))) as executor:
                    future_to_doc = {
                        executor.submit(self._download_single_document, downloader, doc, tender_folder): doc
                        for doc in batch
                        if doc.get('document_links')
                    }
                    
                    for future in as_completed(future_to_doc):
                        doc = future_to_doc[future]
                        file_name = doc.get('file_name', 'Документ')
                        try:
                            downloaded_path = future.result()
                            if downloaded_path:
                                downloaded_count += 1
                                self.progress_updated.emit(downloaded_count, total_docs, file_name)
                                logger.info(f"✅ Скачан: {file_name}")
                        except Exception as error:
                            logger.error(f"❌ Ошибка при скачивании {file_name}: {error}")
                            continue
            
            self.finished.emit(downloaded_count, total_docs, tender_folder)
            
        except Exception as error:
            logger.error(f"Критическая ошибка при скачивании документов: {error}")
            self.error_occurred.emit(f"Ошибка при скачивании документов: {str(error)}")
    
    def _download_single_document(self, downloader: DocumentDownloader, doc: Dict[str, Any], target_dir: Path) -> Optional[Path]:
        """Скачивание одного документа (для использования в ThreadPoolExecutor)"""
        try:
            return downloader.download_document(doc, target_dir=target_dir)
        except Exception as error:
            logger.error(f"Ошибка при скачивании документа: {error}")
            return None
    
    def _determine_registry_type(self) -> str:
        """Определяет тип реестра (44ФЗ/223ФЗ)"""
        raw_value = (
            self.tender_data.get('registry_type')
            or self.tender_data.get('law')
            or ''
        )
        value = str(raw_value).lower()
        if '223' in value:
            return '223fz'
        return '44fz'

