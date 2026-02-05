"""
MODULE: modules.ii.dialogs.task_creation_dialog
RESPONSIBILITY: Диалог для создания списка задач с помощью AI.
ALLOWED: PyQt5, modules.ii.ai_base, modules.styles.*
FORBIDDEN: Прямой доступ к БД или сложная бизнес-логика управления задачами.
ERRORS: None.

Специализированный диалог для создания задач на основе описания проекта.
"""

from typing import Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

from modules.ii.ai_base import AIChatDialog
from modules.styles.general_styles import apply_label_style, apply_input_style


class TaskCreationDialog(AIChatDialog):
    """Диалог для создания списка задач"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Создание задач", parent)

    def create_content(self):
        """Создание контента для создания задач"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        project_label = QLabel("Описание проекта/цели:")
        apply_label_style(project_label, 'h3')
        layout.addWidget(project_label)

        self.project_input = QTextEdit()
        self.project_input.setMaximumHeight(150)
        apply_input_style(self.project_input, 'large')
        layout.addWidget(self.project_input)

        criteria_label = QLabel("Критерии задач:")
        apply_label_style(criteria_label, 'h3')
        layout.addWidget(criteria_label)

        self.criteria_input = QTextEdit()
        self.criteria_input.setMaximumHeight(100)
        apply_input_style(self.criteria_input, 'large')
        self.criteria_input.setPlaceholderText("Например: сроки, приоритеты, ресурсы...")
        layout.addWidget(self.criteria_input)

        return widget