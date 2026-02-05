"""
MODULE: modules.ii.ai_base
RESPONSIBILITY: Базовый класс для AI диалогов и общая логика.
ALLOWED: PyQt5, loguru, modules.styles.*
FORBIDDEN: Конкретная бизнес-логика диалогов.
ERRORS: None.

Базовый класс для всех AI диалогов с общей функциональностью.
"""

from typing import Optional

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QMessageBox
from PyQt5.QtCore import Qt

from loguru import logger
from modules.styles.general_styles import apply_button_style, apply_label_style


class AIChatDialog(QDialog):
    """Базовое диалоговое окно для специфических задач"""

    def __init__(self, task_type: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.task_type = task_type
        from modules.styles.ui_config import configure_dialog
        configure_dialog(self, f"AI Ассистент - {task_type}", size_preset="ai_chat")
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        """Инициализация базового UI"""
        layout = QVBoxLayout(self)

        # Заголовок с единым стилем
        title = QLabel(f"🤖 {self.task_type}")
        apply_label_style(title, 'h1')
        layout.addWidget(title)

        # Контент
        self.content_widget = self.create_content()
        layout.addWidget(self.content_widget)

        # Кнопки с едиными стилями
        button_layout = QHBoxLayout()
        self.btn_process = QPushButton("Обработать")
        apply_button_style(self.btn_process, 'primary')
        self.btn_process.clicked.connect(self.process_task)

        self.btn_cancel = QPushButton("Отмена")
        apply_button_style(self.btn_cancel, 'outline')
        self.btn_cancel.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_process)
        layout.addLayout(button_layout)

    def create_content(self):
        """Создание контента - переопределяется в дочерних классах"""
        return QLabel("Базовый контент")

    def process_task(self):
        """Обработка задачи - базовая реализация"""
        try:
            logger.info(f"Обработка задачи: {self.task_type}")
            # Здесь будет логика обработки
            QMessageBox.information(self, "Успех", "Задача обработана успешно!")
            self.accept()
        except Exception as e:
            logger.error(f"Ошибка обработки: {e}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {str(e)}")