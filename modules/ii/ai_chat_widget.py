"""
MODULE: modules.ii.ai_chat_widget
RESPONSIBILITY: Основной виджет чата с ИИ и управление диалогами.
ALLOWED: PyQt5, modules.ii.dialogs.*, modules.ii.chat_widgets, modules.styles.*
FORBIDDEN: Прямой доступ к БД или сложная бизнес-логика AI.
ERRORS: None.

Главный виджет чата с ИИ, координирующий работу диалогов.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QFrame
from PyQt5.QtCore import Qt

from loguru import logger
from modules.styles.general_styles import apply_button_style, apply_frame_style, apply_combobox_style
from modules.styles.ii_styles import apply_chat_input_panel_style

# Импортируем наши диалоги
from modules.ii.dialogs.email_reply_dialog import EmailReplyDialog
from modules.ii.dialogs.new_email_dialog import NewEmailDialog
from modules.ii.dialogs.text_analysis_dialog import TextAnalysisDialog
from modules.ii.dialogs.task_creation_dialog import TaskCreationDialog


class AIChatWidget(QWidget):
    """Основной виджет чата с ИИ"""

    def __init__(self):
        super().__init__()
        logger.info("Инициализация AI Chat модуля")
        self.current_agent = None
        self.init_ui()

    def init_ui(self):
        """Инициализация основного UI"""
        try:
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(15, 15, 15, 15)
            main_layout.setSpacing(10)

            # Верхняя панель с выбором агента
            top_panel = self.create_top_panel()
            main_layout.addWidget(top_panel)

            # Основная область - чат (заглушка)
            chat_placeholder = QFrame()
            apply_frame_style(chat_placeholder, 'card')
            chat_placeholder.setMinimumHeight(400)
            main_layout.addWidget(chat_placeholder, 1)

            # Нижняя панель ввода
            input_panel = self.create_input_panel()
            main_layout.addWidget(input_panel)

        except Exception as e:
            logger.error(f"Ошибка инициализации UI: {e}")

    def create_top_panel(self):
        """Создание верхней панели с выбором типа задачи"""
        panel = QFrame()
        apply_frame_style(panel, 'card')
        
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        
        label = QLabel("Тип задачи:")
        layout.addWidget(label)
        
        self.agent_combo = QComboBox()
        apply_combobox_style(self.agent_combo)
        self.agent_combo.addItems([
            "Ответить на письмо",
            "Новое письмо", 
            "Анализ текста",
            "Создание задач"
        ])
        layout.addWidget(self.agent_combo)
        
        self.btn_open = QPushButton("Открыть")
        apply_button_style(self.btn_open, 'primary')
        self.btn_open.clicked.connect(self.open_selected_dialog)
        layout.addWidget(self.btn_open)
        
        layout.addStretch()
        return panel

    def create_input_panel(self):
        """Создание панели ввода (заглушка)"""
        panel = QFrame()
        apply_chat_input_panel_style(panel)
        return panel

    def open_selected_dialog(self):
        """Открытие выбранного диалога"""
        try:
            selected = self.agent_combo.currentText()
            
            if selected == "Ответить на письмо":
                dialog = EmailReplyDialog(self)
            elif selected == "Новое письмо":
                dialog = NewEmailDialog(self) 
            elif selected == "Анализ текста":
                dialog = TextAnalysisDialog(self)
            elif selected == "Создание задач":
                dialog = TaskCreationDialog(self)
            else:
                return
                
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Ошибка открытия диалога: {e}")