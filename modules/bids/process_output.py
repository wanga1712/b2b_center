"""
MODULE: modules.bids.process_output
RESPONSIBILITY: Dialog and Thread for capturing and displaying external process output.
ALLOWED: PyQt5, loguru, typing.
FORBIDDEN: Business logic.
ERRORS: None.

Модуль для отображения вывода процессов обработки документов.
"""

from typing import Optional, Callable

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger

from modules.styles.general_styles import (
    apply_label_style, apply_button_style, apply_text_edit_style
)


class ProcessOutputReader(QThread):
    """Поток для чтения вывода процесса в реальном времени"""
    
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)
    
    def __init__(self, process):
        super().__init__()
        self.process = process
    
    def run(self):
        """Чтение вывода процесса"""
        try:
            # Для всех платформ используем простой подход с readline
            # stderr объединен с stdout через stderr=subprocess.STDOUT
            while True:
                output = self.process.stdout.readline()
                if not output:
                    # Если строка пустая, проверяем, завершен ли процесс
                    if self.process.poll() is not None:
                        break
                    # Если процесс еще работает, продолжаем ждать
                    continue
                # Отправляем строку (убираем только завершающие символы новой строки)
                self.output_signal.emit(output.rstrip('\n\r'))
            
            # Процесс завершен, читаем оставшийся вывод
            # Используем communicate() только если процесс уже завершен
            try:
                remaining_output, _ = self.process.communicate(timeout=0.1)
                if remaining_output:
                    for line in remaining_output.splitlines():
                        if line.strip():
                            self.output_signal.emit(line.strip())
            except Exception:
                # Игнорируем ошибки при чтении оставшегося вывода
                pass
            
            # Отправляем код завершения
            return_code = self.process.returncode if self.process.returncode is not None else 0
            self.finished_signal.emit(return_code)
        except Exception as e:
            logger.error(f"Ошибка чтения вывода процесса: {e}")
            self.output_signal.emit(f"[ERROR] Ошибка чтения вывода: {e}")
            self.finished_signal.emit(-1)


class ProcessOutputDialog(QDialog):
    """Диалог для отображения вывода консоли процесса"""
    
    def __init__(self, parent=None, title="Вывод процесса", on_finished: Optional[Callable[[int], None]] = None):
        super().__init__(parent)
        from modules.styles.ui_config import configure_dialog
        configure_dialog(self, title, size_preset="xlarge", min_width=800, min_height=600)
        self.setModal(False)  # Не модальное окно, чтобы можно было работать с приложением
        self.process = None
        self.reader_thread = None
        self._on_finished_callback = on_finished
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса диалога"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Заголовок
        title_label = QLabel("📊 Вывод процесса обработки документов")
        apply_label_style(title_label, 'h2')
        layout.addWidget(title_label)
        
        # Текстовое поле для вывода
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        apply_text_edit_style(self.output_text, 'log')
        layout.addWidget(self.output_text)
        
        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.close_button = QPushButton("Закрыть")
        apply_button_style(self.close_button, 'outline')
        self.close_button.clicked.connect(self.close)
        self.close_button.setEnabled(False)  # Отключаем до завершения процесса
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def start_process(self, process):
        """Запуск процесса и начало чтения вывода"""
        self.process = process
        
        # Создаем и запускаем поток чтения
        self.reader_thread = ProcessOutputReader(process)
        self.reader_thread.output_signal.connect(self.append_output)
        self.reader_thread.finished_signal.connect(self.on_process_finished)
        self.reader_thread.start()
        
        self.append_output("Процесс запущен...")
    
    def append_output(self, text: str):
        """Добавление текста в вывод"""
        if text:
            self.output_text.append(text)
            # Автопрокрутка вниз
            scrollbar = self.output_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def on_process_finished(self, return_code: int):
        """Обработка завершения процесса"""
        # #region agent log
        import json
        import time
        log_path = r"c:\Users\wangr\PycharmProjects\pythonProject89\.cursor\debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A",
                    "location": "process_output.py:on_process_finished:entry",
                    "message": "Процесс анализа завершен",
                    "data": {
                        "return_code": return_code,
                        "has_callback": self._on_finished_callback is not None
                    },
                    "timestamp": int(time.time() * 1000)
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        
        if return_code == 0:
            self.append_output("\n[SUCCESS] Процесс успешно завершен.")
        else:
            self.append_output(f"\n[ERROR] Процесс завершен с кодом: {return_code}")
        
        self.close_button.setEnabled(True)
        
        # Уведомляем внешний код о завершении процесса (для сброса состояний)
        if self._on_finished_callback:
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "A",
                        "location": "process_output.py:on_process_finished:before_callback",
                        "message": "Вызов callback после завершения анализа",
                        "data": {"return_code": return_code},
                        "timestamp": int(time.time() * 1000)
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            try:
                self._on_finished_callback(return_code)
                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "A",
                            "location": "process_output.py:on_process_finished:after_callback",
                            "message": "Callback выполнен успешно",
                            "data": {"return_code": return_code},
                            "timestamp": int(time.time() * 1000)
                        }, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
            except Exception as callback_error:
                logger.error(f"Ошибка в обработчике завершения процесса: {callback_error}")
                # #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "A",
                            "location": "process_output.py:on_process_finished:callback_error",
                            "message": "Ошибка в callback",
                            "data": {"error": str(callback_error)},
                            "timestamp": int(time.time() * 1000)
                        }, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                # #endregion
        else:
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "A",
                        "location": "process_output.py:on_process_finished:no_callback",
                        "message": "Нет callback для обновления карточек",
                        "data": {"return_code": return_code},
                        "timestamp": int(time.time() * 1000)
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        if self.reader_thread and self.reader_thread.isRunning():
            # Если процесс еще выполняется, просто закрываем окно
            # Процесс продолжит работу в фоне
            pass
        super().closeEvent(event)

