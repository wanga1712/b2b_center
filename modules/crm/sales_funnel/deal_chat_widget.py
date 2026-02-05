"""
MODULE: modules.crm.sales_funnel.deal_chat_widget
RESPONSIBILITY: Chat UI widget for deal discussions.
ALLOWED: PyQt5, loguru, modules.styles.*, modules.crm.sales_funnel.deal_chat_service, modules.crm.sales_funnel.deal_chat_ai_agent.
FORBIDDEN: Direct DB access.
ERRORS: None.

Виджет чата для детальной карточки сделки.
Компактная версия с возможностью раскрыть в отдельное окно.
"""

from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QComboBox,
    QScrollArea,
    QFrame,
    QMessageBox,
    QCheckBox,
    QDialog,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from loguru import logger

from modules.styles.general_styles import (
    apply_label_style,
    apply_button_style,
    apply_input_style,
    apply_combobox_style,
    COLORS,
    FONT_SIZES,
)
from modules.crm.sales_funnel.deal_chat_service import DealChatService
from modules.crm.sales_funnel.deal_chat_ai_agent import DealChatAIAgent


class DealChatExpandedDialog(QDialog):
    """Диалоговое окно для раскрытого чата."""
    
    def __init__(self, original_widget: 'DealChatWidget', parent=None):
        super().__init__(parent)
        self.setWindowTitle("💬 Чат по сделке")
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Создаем новый виджет чата с теми же параметрами
        expanded_widget = DealChatWidget(
            deal_id=original_widget.deal_id,
            current_user_id=original_widget.current_user_id,
            chat_service=original_widget.chat_service,
            detail_service=original_widget.detail_service,
            parent=self,
        )
        # Загружаем сообщения
        expanded_widget.load_messages()
        
        # Убираем кнопку раскрыть и делаем область сообщений большой
        expanded_widget.expand_button.hide()
        expanded_widget.scroll_area.setMaximumHeight(16777215)
        
        layout.addWidget(expanded_widget)
        
        # Кнопка закрытия
        btn_close = QPushButton("Закрыть")
        apply_button_style(btn_close, "secondary")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)


class DealChatWidget(QWidget):
    """Виджет чата по сделке с выбором собеседника и AI-агентом."""

    message_sent = pyqtSignal(int, str, str)  # deal_id, sender_type, message_text

    def __init__(
        self,
        deal_id: int,
        current_user_id: int,
        chat_service: DealChatService,
        detail_service: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.deal_id = deal_id
        self.current_user_id = current_user_id
        self.chat_service = chat_service
        self.detail_service = detail_service
        self.ai_agent = DealChatAIAgent()
        self.messages: List[Dict[str, Any]] = []
        self.is_compact = True
        self.init_ui()
        self.load_messages()
        self.load_users()

    def init_ui(self):
        """Инициализация интерфейса чата."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Верхняя панель: галочка ИИ, выбор модели, выбор собеседника, кнопка раскрыть
        header_layout = QHBoxLayout()
        
        # Галочка для выбора ИИ
        self.ai_checkbox = QCheckBox("🤖 ИИ Ассистент")
        self.ai_checkbox.setChecked(True)
        self.ai_checkbox.stateChanged.connect(self._on_ai_toggled)
        header_layout.addWidget(self.ai_checkbox)
        
        # Выбор модели OpenRouter (только если ИИ включен)
        self.model_combo = QComboBox()
        apply_combobox_style(self.model_combo)
        self._load_ai_models()
        self.model_combo.setEnabled(True)
        header_layout.addWidget(QLabel("Модель:"))
        header_layout.addWidget(self.model_combo)
        
        # Выбор собеседника (только если ИИ выключен)
        self.companion_combo = QComboBox()
        apply_combobox_style(self.companion_combo)
        self.companion_combo.setEnabled(False)
        header_layout.addWidget(QLabel("Собеседник:"))
        header_layout.addWidget(self.companion_combo)
        
        header_layout.addStretch()
        
        # Кнопка раскрыть
        self.expand_button = QPushButton("🔍 Раскрыть")
        apply_button_style(self.expand_button, "secondary")
        self.expand_button.clicked.connect(self._expand_chat)
        header_layout.addWidget(self.expand_button)
        
        layout.addLayout(header_layout)

        # Область сообщений (прокручиваемая) - компактная версия
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(
            f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background: {COLORS['white']};
            }}
        """
        )
        # Компактная высота - увеличена для лучшей видимости
        self.scroll_area.setMaximumHeight(300)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setSpacing(4)  # Уменьшено для компактности
        self.messages_layout.setContentsMargins(4, 4, 4, 4)  # Уменьшено
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area)

        # Поле ввода и кнопка отправки
        input_layout = QHBoxLayout()
        self.message_input = QTextEdit()
        self.message_input.setMaximumHeight(60)
        self.message_input.setPlaceholderText("Введите комментарий или сообщение...")
        apply_input_style(self.message_input)
        input_layout.addWidget(self.message_input)

        self.send_button = QPushButton("Отправить")
        apply_button_style(self.send_button, "primary")
        self.send_button.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.send_button)

        layout.addLayout(input_layout)

    def _load_ai_models(self):
        """Загрузка списка моделей OpenRouter."""
        # Список моделей OpenRouter - дешевые для тестов вначале, дорогие в конце
        models = [
            # Очень дешевые модели DeepSeek (дипсик) 🔥
            ("deepseek/deepseek-chat", "DeepSeek Chat (очень дешево) 🔥"),
            ("deepseek/deepseek-coder", "DeepSeek Coder (очень дешево)"),
            # Дешевые модели для тестирования
            ("openai/gpt-3.5-turbo", "GPT-3.5 Turbo (дешево)"),
            ("google/gemini-flash-1.5", "Gemini Flash 1.5 (дешево)"),
            ("meta-llama/llama-3-8b-instruct", "Llama 3 8B (дешево)"),
            ("anthropic/claude-3-haiku", "Claude 3 Haiku (дешево)"),
            # Средние модели
            ("google/gemini-pro-1.5", "Gemini Pro 1.5"),
            ("meta-llama/llama-3-70b-instruct", "Llama 3 70B"),
            # Дорогие модели
            ("openai/gpt-4-turbo", "GPT-4 Turbo"),
            ("openai/gpt-4", "GPT-4"),
            ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet"),
            ("anthropic/claude-3-opus", "Claude 3 Opus"),
        ]
        for model_id, model_name in models:
            self.model_combo.addItem(model_name, model_id)

    def _on_ai_toggled(self, state):
        """Обработка переключения галочки ИИ."""
        is_ai_enabled = state == Qt.Checked
        self.model_combo.setEnabled(is_ai_enabled)
        self.companion_combo.setEnabled(not is_ai_enabled)

    def _expand_chat(self):
        """Раскрытие чата в отдельное окно."""
        try:
            # Создаем диалог с новым виджетом чата
            expanded_dialog = DealChatExpandedDialog(self, self.parent())
            
            # Показываем диалог (модальный)
            expanded_dialog.exec_()
            
            # После закрытия диалога обновляем сообщения в компактном виджете
            self.load_messages()
        except Exception as exc:
            logger.error(f"Ошибка при раскрытии чата: {exc}", exc_info=True)

    def load_users(self):
        """Загрузка списка пользователей для выбора собеседника."""
        try:
            users = self.chat_service.get_users_list()
            for user in users:
                user_display = f"👤 Пользователь #{user['id']}"
                if user.get("email"):
                    user_display += f" ({user['email']})"
                self.companion_combo.addItem(user_display, f"user_{user['id']}")
        except Exception as exc:
            logger.error(f"Ошибка при загрузке пользователей: {exc}", exc_info=True)

    def load_messages(self):
        """Загрузка сообщений чата."""
        try:
            self.messages = self.chat_service.get_messages(self.deal_id)
            self._render_messages()
            # Прокрутка вниз
            self._scroll_to_bottom()
        except Exception as exc:
            logger.error(f"Ошибка при загрузке сообщений: {exc}", exc_info=True)

    def _scroll_to_bottom(self):
        """Прокрутка вниз к последнему сообщению."""
        scrollbar = self.scroll_area.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def _render_messages(self):
        """Отрисовка сообщений в контейнере."""
        # Очищаем старые сообщения (кроме stretch)
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Добавляем сообщения
        for msg in self.messages:
            message_widget = self._create_message_widget(msg)
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, message_widget)

    def _create_message_widget(self, message: Dict[str, Any]) -> QWidget:
        """Создание виджета одного сообщения в стиле ICQ/мессенджера."""
        sender_type = message.get("sender_type", "user")
        sender_id = message.get("sender_id")
        is_current_user = sender_id == self.current_user_id
        
        # Контейнер для выравнивания (слева/справа)
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)
        
        # Определяем цвет и иконку
        if sender_type == "ai_agent":
            bg_color = "#E8F5E9"  # Светло-зеленый для AI
            icon = "🤖"
            sender_name = "AI-Ассистент"
            align_right = False
        elif is_current_user:
            bg_color = "#E3F2FD"  # Светло-синий для текущего пользователя
            icon = "👤"
            sender_name = "Вы"
            align_right = True
        else:
            bg_color = "#F5F5F5"  # Серый для других пользователей
            icon = "👤"
            sender_name = f"Пользователь #{sender_id}"
            align_right = False
        
        # Добавляем отступ слева или справа
        if align_right:
            container_layout.addStretch()
        
        # Пузырь сообщения (как в ICQ)
        bubble = QFrame()
        bubble.setMaximumWidth(500)  # Ограничиваем ширину
        bubble.setStyleSheet(
            f"""
            QFrame {{
                background: {bg_color};
                border-radius: 12px;
                padding: 6px 10px;
                margin: 1px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setSpacing(2)
        bubble_layout.setContentsMargins(6, 4, 6, 4)
        
        # Заголовок: иконка + отправитель
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 12pt;")
        header_layout.addWidget(icon_label)
        
        sender_label = QLabel(sender_name)
        sender_label.setStyleSheet("font-weight: bold; font-size: 9pt; color: #555;")
        header_layout.addWidget(sender_label)
        header_layout.addStretch()
        
        bubble_layout.addLayout(header_layout)
        
        # Текст сообщения
        message_text = message.get("message_text", "")
        text_label = QLabel(message_text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet("font-size: 10pt; color: #000; line-height: 1.4;")
        bubble_layout.addWidget(text_label)
        
        # Время внизу справа
        created_at = message.get("created_at")
        if created_at:
            from datetime import datetime
            if isinstance(created_at, str):
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    time_str = dt.strftime("%H:%M")
                except:
                    time_str = str(created_at)[:19].replace("T", " ")
            else:
                time_str = created_at.strftime("%H:%M") if hasattr(created_at, 'strftime') else str(created_at)
            
            time_label = QLabel(time_str)
            time_label.setStyleSheet("font-size: 8pt; color: #888;")
            time_label.setAlignment(Qt.AlignRight)
            bubble_layout.addWidget(time_label)
        
        container_layout.addWidget(bubble)
        
        # Добавляем отступ слева или справа
        if not align_right:
            container_layout.addStretch()
        
        return container

    def _on_companion_changed(self, index: int):
        """Обработка изменения выбранного собеседника."""
        # Можно перезагрузить сообщения или отфильтровать по собеседнику
        pass

    def _on_send_clicked(self):
        """Обработка отправки сообщения."""
        message_text = self.message_input.toPlainText().strip()
        if not message_text:
            return

        # Отправляем сообщение от пользователя
        sender_type = "user"
        sender_id = self.current_user_id

        message_id = self.chat_service.send_message(
            deal_id=self.deal_id,
            sender_id=sender_id,
            sender_type=sender_type,
            message_text=message_text,
        )

        if message_id:
            self.message_input.clear()
            self.load_messages()
            self.message_sent.emit(self.deal_id, sender_type, message_text)

            # Если ИИ включен, генерируем ответ
            if self.ai_checkbox.isChecked():
                self._send_ai_response(message_text)
        else:
            # Получаем детальную ошибку из сервиса
            error_info = getattr(self.chat_service, '_last_error', None)
            if error_info:
                error_text = f"""❌ Не удалось отправить сообщение

Тип ошибки: {error_info.get('error_type', 'Unknown')}
Ошибка: {error_info.get('error', 'Неизвестная ошибка')}

Детали:
{error_info.get('traceback', 'Нет деталей')}

💡 Решение:
Если ошибка связана с отсутствием таблицы 'deal_chat', 
выполните SQL миграцию из файла:
scripts/sql_queries/add_deal_chat_table.sql

Скопируйте текст ошибки для отладки."""
            else:
                error_text = "Не удалось отправить сообщение.\n\nПроверьте логи приложения для деталей."
            
            from PyQt5.QtWidgets import QMessageBox, QTextEdit, QVBoxLayout, QDialog, QPushButton
            from PyQt5.QtCore import Qt
            
            # Создаем диалог с детальной информацией об ошибке
            error_dialog = QDialog(self)
            error_dialog.setWindowTitle("Ошибка отправки сообщения")
            error_dialog.resize(700, 500)
            
            layout = QVBoxLayout(error_dialog)
            
            # Текст ошибки (выделяемый)
            error_text_edit = QTextEdit()
            error_text_edit.setPlainText(error_text)
            error_text_edit.setReadOnly(True)
            error_text_edit.setStyleSheet("font-family: 'Courier New', monospace; font-size: 10pt;")
            layout.addWidget(error_text_edit)
            
            # Кнопка закрытия
            btn_close = QPushButton("Закрыть")
            apply_button_style(btn_close, "secondary")
            btn_close.clicked.connect(error_dialog.accept)
            layout.addWidget(btn_close)
            
            error_dialog.exec_()

    def _send_ai_response(self, user_message: str):
        """Отправка ответа AI-агента на сообщение пользователя."""
        try:
            # Получаем контекст сделки
            deal_context = None
            if self.detail_service:
                # Используем данные из кеша сервиса
                deal_context = self.detail_service._deal_card_cache.get(self.deal_id, {})

            # Получаем выбранную модель
            model_id = self.model_combo.currentData()
            
            # Генерируем ответ через AI-агента
            ai_response = self.ai_agent.generate_response(
                user_message=user_message,
                deal_context=deal_context,
                conversation_history=self.messages,
                model_id=model_id,
            )

            # Отправляем ответ AI-агента
            self.chat_service.send_message(
                deal_id=self.deal_id,
                sender_id=None,
                sender_type="ai_agent",
                message_text=ai_response,
                metadata={
                    "agent_name": self.ai_agent.name,
                    "model_id": model_id,
                },
            )

            # Перезагружаем сообщения для отображения ответа
            self.load_messages()
        except Exception as exc:
            logger.error(f"Ошибка при генерации ответа AI-агента: {exc}", exc_info=True)
            QMessageBox.warning(self, "Ошибка", f"Не удалось получить ответ от AI: {exc}")
