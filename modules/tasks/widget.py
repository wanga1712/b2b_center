from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

class TasksWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("✅ Задачи")
        title.setStyleSheet("font-size:22px; margin-bottom:14px;")
        layout.addWidget(title)
        layout.addWidget(QTextEdit("Список задач, статусы, дедлайны, напоминания по процессам."))
