"""
MODULE: modules.ii.dialogs.email_reply_dialog
RESPONSIBILITY: Диалог для ответа на письмо с помощью AI.
ALLOWED: PyQt5, modules.ii.ai_base, modules.styles.*
FORBIDDEN: Прямой доступ к БД или бизнес-логике обработки писем.
ERRORS: None.

Специализированный диалог для ответа на электронные письма.
"""

from typing import Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit

from modules.ii.ai_base import AIChatDialog
from modules.styles.general_styles import apply_label_style, apply_input_style


class EmailReplyDialog(AIChatDialog):
    """Диалог для ответа на письмо"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Ответить на письмо", parent)

    def create_content(self):
        """Создание контента для ответа на письмо"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Поля ввода с едиными стилями
        fields = [
            ("От кого:", QLineEdit()),
            ("Кому:", QLineEdit()),
            ("Тема:", QLineEdit()),
            ("Текст письма:", QTextEdit())
        ]

        for label_text, field in fields:
            label = QLabel(label_text)
            apply_label_style(label, 'h3')
            layout.addWidget(label)

            if isinstance(field, QTextEdit):
                field.setMaximumHeight(200)
                apply_input_style(field, 'large')
            else:
                apply_input_style(field)
            layout.addWidget(field)

        return widget