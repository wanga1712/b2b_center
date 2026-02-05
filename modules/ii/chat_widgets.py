"""
MODULE: modules.ii.chat_widgets
RESPONSIBILITY: Виджеты для чата с ИИ (сообщения и базовые компоненты).
ALLOWED: PyQt5, modules.styles.*
FORBIDDEN: Бизнес-логика чата или обработка сообщений.
ERRORS: None.

Компоненты для отображения сообщений в чате с ИИ.
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QSizePolicy

from modules.styles.general_styles import apply_label_style, apply_text_color
from modules.styles.ii_styles import apply_chat_message_style


class ChatMessageWidget(QFrame):
    """Виджет сообщения в чате"""

    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.init_ui(text)

    def init_ui(self, text: str):
        """Инициализация UI сообщения"""
        apply_chat_message_style(self, self.is_user)

        layout = QVBoxLayout(self)
        label = QLabel(text)
        apply_label_style(label, 'normal')
        apply_text_color(label, 'white' if self.is_user else 'text_dark')
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        layout.addWidget(label)

        # Выравнивание
        if self.is_user:
            self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
            layout.setAlignment(Qt.AlignRight)
        else:
            self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
            layout.setAlignment(Qt.AlignLeft)