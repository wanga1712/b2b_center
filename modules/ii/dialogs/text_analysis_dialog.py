"""
MODULE: modules.ii.dialogs.text_analysis_dialog
RESPONSIBILITY: Диалог для анализа текста с помощью AI.
ALLOWED: PyQt5, modules.ii.ai_base, modules.styles.*
FORBIDDEN: Прямой доступ к БД или сложная бизнес-логика анализа.
ERRORS: None.

Специализированный диалог для анализа текстовых данных.
"""

from typing import Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QFileDialog

from modules.ii.ai_base import AIChatDialog
from modules.styles.general_styles import apply_label_style, apply_input_style, apply_button_style
from loguru import logger


class TextAnalysisDialog(AIChatDialog):
    """Диалог для анализа текста"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Анализ текста", parent)

    def create_content(self):
        """Создание контента для анализа текста"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Кнопки загрузки файлов с едиными стилями
        file_layout = QHBoxLayout()

        file_label = QLabel("Загрузить файл:")
        apply_label_style(file_label, 'normal')
        file_layout.addWidget(file_label)

        self.btn_load_txt = QPushButton("📄 TXT")
        apply_button_style(self.btn_load_txt, 'outline')
        self.btn_load_txt.clicked.connect(self.load_file)

        self.btn_load_pdf = QPushButton("📊 PDF")
        apply_button_style(self.btn_load_pdf, 'outline')
        self.btn_load_pdf.clicked.connect(self.load_file)

        self.btn_load_excel = QPushButton("📈 Excel")
        apply_button_style(self.btn_load_excel, 'outline')
        self.btn_load_excel.clicked.connect(self.load_file)

        self.btn_load_word = QPushButton("📝 Word")
        apply_button_style(self.btn_load_word, 'outline')
        self.btn_load_word.clicked.connect(self.load_file)

        file_layout.addStretch()
        layout.addLayout(file_layout)

        # Поле для текста с единым стилем
        text_label = QLabel("Или введите текст:")
        apply_label_style(text_label, 'h3')
        layout.addWidget(text_label)

        self.text_input = QTextEdit()
        self.text_input.setMaximumHeight(250)
        apply_input_style(self.text_input, 'large')
        layout.addWidget(self.text_input)

        return widget

    def load_file(self):
        """Загрузка файла - базовая реализация"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Выберите файл", "",
                "Все файлы (*.*);;TXT (*.txt);;PDF (*.pdf);;Excel (*.xlsx *.xls);;Word (*.docx *.doc)"
            )
            if file_path:
                logger.info(f"Загружен файл: {file_path}")
                # Здесь будет парсинг файла
                self.text_input.setText(f"Содержимое файла: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки файла: {e}")