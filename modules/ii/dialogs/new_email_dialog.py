"""
MODULE: modules.ii.dialogs.new_email_dialog
RESPONSIBILITY: Диалог для создания нового письма с помощью AI.
ALLOWED: PyQt5, modules.ii.ai_base, modules.styles.*
FORBIDDEN: Прямой доступ к БД или бизнес-логике отправки писем.
ERRORS: None.

Специализированный диалог для создания новых электронных писем.
"""

from typing import Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit

from modules.ii.ai_base import AIChatDialog
from modules.styles.general_styles import apply_label_style, apply_input_style


class NewEmailDialog(AIChatDialog):
    """Диалог для нового письма"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Новое письмо", parent)

    def create_content(self):
        """Создание контента для нового письма"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        fields = [
            ("Кому:", QLineEdit()),
            ("Тема:", QLineEdit()),
            ("Текст:", QTextEdit())
        ]

        for label_text, field in fields:
            label = QLabel(label_text)
            apply_label_style(label, 'h3')
            layout.addWidget(label)

            if isinstance(field, QTextEdit):
                field.setMaximumHeight(250)
                apply_input_style(field, 'large')
            else:
                apply_input_style(field)
            layout.addWidget(field)

        return widget