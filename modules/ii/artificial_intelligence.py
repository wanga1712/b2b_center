import logging
from loguru import logger
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QTextEdit,
    QPushButton, QLabel, QFrame, QScrollArea, QLineEdit,
    QDialog, QFileDialog, QMessageBox, QSplitter, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal

# Импортируем единые стили
from modules.styles.general_styles import (
    apply_button_style, apply_input_style, apply_label_style,
    apply_combobox_style, apply_frame_style, COLORS, FONT_SIZES
)


class AIChatDialog(QDialog):
    """Базовое диалоговое окно для специфических задач"""

    def __init__(self, task_type, parent=None):
        super().__init__(parent)
        self.task_type = task_type
        from modules.styles.ui_config import configure_dialog
        configure_dialog(self, f"AI Ассистент - {task_type}", size_preset="ai_chat")
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
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
        """Переопределяется в дочерних классах"""
        return QLabel("Базовый контент")

    def process_task(self):
        """Обработка задачи - заглушка"""
        try:
            logger.info(f"Обработка задачи: {self.task_type}")
            # Здесь будет логика обработки
            QMessageBox.information(self, "Успех", "Задача обработана успешно!")
            self.accept()
        except Exception as e:
            logger.error(f"Ошибка обработки: {e}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {str(e)}")


class EmailReplyDialog(AIChatDialog):
    """Диалог для ответа на письмо"""

    def __init__(self, parent=None):
        super().__init__("Ответить на письмо", parent)

    def create_content(self):
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


class NewEmailDialog(AIChatDialog):
    """Диалог для нового письма"""

    def __init__(self, parent=None):
        super().__init__("Новое письмо", parent)

    def create_content(self):
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


class TextAnalysisDialog(AIChatDialog):
    """Диалог для анализа текста"""

    def __init__(self, parent=None):
        super().__init__("Анализ текста", parent)

    def create_content(self):
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
        """Загрузка файла - заглушка"""
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


class TaskCreationDialog(AIChatDialog):
    """Диалог для создания списка задач"""

    def __init__(self, parent=None):
        super().__init__("Создание задач", parent)

    def create_content(self):
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


class ChatMessageWidget(QFrame):
    """Виджет сообщения в чате"""

    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.init_ui(text)

    def init_ui(self, text):
        # Используем стили из общего модуля Bitrix24
        background_color = COLORS['primary'] if self.is_user else '#E3F2FD'
        text_color = 'white' if self.is_user else COLORS['text_dark']

        self.setStyleSheet(f"""
            ChatMessageWidget {{
                background: {background_color};
                border-radius: 12px;
                padding: 12px 16px;
                margin: 8px 0px;
                max-width: 80%;
            }}
        """)

        layout = QVBoxLayout(self)
        label = QLabel(text)
        label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-size: {FONT_SIZES['normal']};
                background: transparent;
            }}
        """)
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


class AIChatWidget(QWidget):
    """Основной виджет чата с ИИ"""

    def __init__(self):
        super().__init__()
        logger.info("Инициализация AI Chat модуля")
        self.current_agent = None
        self.init_ui()

    def init_ui(self):
        try:
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(15, 15, 15, 15)
            main_layout.setSpacing(10)

            # Верхняя панель с выбором агента
            top_panel = self.create_top_panel()
            main_layout.addWidget(top_panel)

            # Основная область - чат
            chat_panel = self.create_chat_panel()
            main_layout.addWidget(chat_panel, 1)

        except Exception as e:
            logger.error(f"Ошибка инициализации UI: {e}")

    def create_top_panel(self):
        """Верхняя панель с выбором типа задачи"""
        panel = QFrame()
        apply_frame_style(panel, 'card')

        layout = QVBoxLayout(panel)  # Вертикальное расположение

        # Лейбл для выбора агента (над выпадающим списком)
        agent_label = QLabel("Выберите режим работы:")
        apply_label_style(agent_label, 'h3')
        layout.addWidget(agent_label)

        # Выпадающий список с агентами
        agent_layout = QHBoxLayout()

        self.agent_combo = QComboBox()
        self.agent_combo.addItems([
            "💬 Чат с ассистентом",
            "📧 Ответить на письмо",
            "✉️ Новое письмо",
            "🔍 Анализ текста",
            "✅ Создание задач"
        ])
        apply_combobox_style(self.agent_combo)
        self.agent_combo.currentTextChanged.connect(self.on_agent_changed)
        agent_layout.addWidget(self.agent_combo)

        # Кнопка загрузки файлов (только для режима чата)
        self.file_button = QPushButton("📎 Прикрепить файл")
        apply_button_style(self.file_button, 'outline')
        self.file_button.clicked.connect(self.attach_file)
        self.file_button.setVisible(True)  # Показываем для всех режимов
        agent_layout.addWidget(self.file_button)

        agent_layout.addStretch()
        layout.addLayout(agent_layout)

        # Описание выбранного агента
        self.agent_description = QLabel()
        apply_label_style(self.agent_description, 'small')
        self.agent_description.setWordWrap(True)
        layout.addWidget(self.agent_description)

        # Обновляем описание
        self.on_agent_changed(self.agent_combo.currentText())

        return panel

    def create_chat_panel(self):
        """Панель чата"""
        panel = QFrame()
        apply_frame_style(panel, 'card')

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Область сообщений
        self.messages_area = QScrollArea()
        self.messages_area.setWidgetResizable(True)
        self.messages_area.setStyleSheet(f"border: none; background: {COLORS['secondary']};")

        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.addStretch()

        self.messages_area.setWidget(self.messages_widget)
        layout.addWidget(self.messages_area, 1)

        # Панель ввода
        input_panel = QFrame()
        input_panel.setStyleSheet(f"background: {COLORS['white']}; border-top: 1px solid {COLORS['border']};")
        input_layout = QHBoxLayout(input_panel)
        input_layout.setContentsMargins(12, 12, 12, 12)

        # Кнопка прикрепления файла в панели ввода
        self.attach_btn = QPushButton("📎")
        self.attach_btn.setFixedSize(40, 40)
        apply_button_style(self.attach_btn, 'outline')
        self.attach_btn.clicked.connect(self.attach_file)
        input_layout.addWidget(self.attach_btn)

        self.message_input = QTextEdit()
        self.message_input.setMaximumHeight(80)
        self.message_input.setPlaceholderText("Введите ваше сообщение...")
        apply_input_style(self.message_input, 'large')
        input_layout.addWidget(self.message_input, 1)

        self.send_button = QPushButton("📤")
        self.send_button.setFixedSize(50, 50)
        apply_button_style(self.send_button, 'primary')
        self.send_button.clicked.connect(self.send_message)

        input_layout.addWidget(self.send_button)
        layout.addWidget(input_panel)

        return panel

    def on_agent_changed(self, agent_name):
        """Обработчик изменения агента"""
        try:
            descriptions = {
                "💬 Чат с ассистентом": "Общение с ИИ на любые темы",
                "📧 Ответить на письмо": "AI поможет составить ответ на входящее письмо",
                "✉️ Новое письмо": "Создание нового письма с нуля",
                "🔍 Анализ текста": "Анализ документов и текстов",
                "✅ Создание задач": "Формирование списка задач по проекту"
            }

            self.agent_description.setText(descriptions.get(agent_name, ""))
            self.current_agent = agent_name

            # Очищаем чат при смене агента
            self.clear_chat()

            # Добавляем приветственное сообщение
            welcome_messages = {
                "💬 Чат с ассистентом": "Привет! Я ваш AI ассистент. Чем могу помочь?",
                "📧 Ответить на письмо": "Готов помочь с ответом на письмо!",
                "✉️ Новое письмо": "Давайте создадим новое письмо!",
                "🔍 Анализ текста": "Загрузите файл или введите текст для анализа",
                "✅ Создание задач": "Опишите проект для создания списка задач"
            }

            self.add_message(welcome_messages.get(agent_name, "Готов к работе!"), False)

        except Exception as e:
            logger.error(f"Ошибка при смене агента: {e}")

    def attach_file(self):
        """Прикрепление файла к чату"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Выберите файл", "",
                "Все файлы (*.*);;"
                "Текстовые файлы (*.txt);;"
                "PDF файлы (*.pdf);;"
                "Excel файлы (*.xlsx *.xls);;"
                "Word документы (*.docx *.doc);;"
                "Изображения (*.png *.jpg *.jpeg *.gif *.bmp)"
            )

            if file_path:
                logger.info(f"Прикреплен файл: {file_path}")

                # Добавляем сообщение о прикрепленном файле
                file_name = file_path.split('/')[-1]
                file_message = f"📎 Прикреплен файл: {file_name}"
                self.add_message(file_message, True)

                # Здесь будет обработка файла (заглушка)
                file_info = f"Файл '{file_name}' загружен успешно. Готов к анализу."
                self.add_message(file_info, False)

        except Exception as e:
            logger.error(f"Ошибка прикрепления файла: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось прикрепить файл: {str(e)}")

    def send_message(self):
        """Отправка сообщения"""
        try:
            message = self.message_input.toPlainText().strip()
            if not message:
                return

            # Добавляем сообщение пользователя
            self.add_message(message, True)
            self.message_input.clear()

            # Обработка специальных агентов
            if self.current_agent != "💬 Чат с ассистентом":
                self.handle_special_agent(message)
            else:
                # Заглушка для общего чата
                self.simulate_ai_response(message)

        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")

    def handle_special_agent(self, message):
        """Обработка специальных агентов"""
        try:
            if self.current_agent == "📧 Ответить на письмо":
                dialog = EmailReplyDialog(self)
                if dialog.exec_():
                    logger.info("Диалог ответа на письмо завершен")

            elif self.current_agent == "✉️ Новое письмо":
                dialog = NewEmailDialog(self)
                if dialog.exec_():
                    logger.info("Диалог нового письма завершен")

            elif self.current_agent == "🔍 Анализ текста":
                dialog = TextAnalysisDialog(self)
                if dialog.exec_():
                    logger.info("Диалог анализа текста завершен")

            elif self.current_agent == "✅ Создание задач":
                dialog = TaskCreationDialog(self)
                if dialog.exec_():
                    logger.info("Диалог создания задач завершен")

            # Добавляем ответ ИИ
            self.add_message("Задача выполнена успешно! Чем еще могу помочь?", False)

        except Exception as e:
            logger.error(f"Ошибка обработки специального агента: {e}")
            self.add_message(f"Произошла ошибка: {str(e)}", False)

    def simulate_ai_response(self, user_message):
        """Заглушка для ответа ИИ"""
        try:
            # Имитация задержки
            import time
            time.sleep(1)

            responses = {
                "привет": "Здравствуйте! Чем могу помочь?",
                "помощь": "Я могу помочь с анализом данных, генерацией отчетов и ответами на вопросы.",
            }

            response = responses.get(user_message.lower(),
                                     "Я проанализировал ваш запрос. Для более точного ответа уточните, пожалуйста, вопрос.")

            self.add_message(response, False)

        except Exception as e:
            logger.error(f"Ошибка симуляции ответа ИИ: {e}")

    def add_message(self, text, is_user=True):
        """Добавление сообщения в чат"""
        try:
            message_widget = ChatMessageWidget(text, is_user)
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, message_widget)

            # Прокрутка вниз
            self.messages_area.verticalScrollBar().setValue(
                self.messages_area.verticalScrollBar().maximum()
            )

        except Exception as e:
            logger.error(f"Ошибка добавления сообщения: {e}")

    def clear_chat(self):
        """Очистка чата"""
        try:
            for i in reversed(range(self.messages_layout.count() - 1)):
                item = self.messages_layout.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()
        except Exception as e:
            logger.error(f"Ошибка очистки чата: {e}")