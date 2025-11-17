from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

class ClientsWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("👥 Клиенты")
        title.setStyleSheet("font-size:22px; margin-bottom:14px;")
        layout.addWidget(title)
        layout.addWidget(QTextEdit("Поиск, карточки клиентов, история, контакты, договоры."))
