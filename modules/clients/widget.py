from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from modules.styles.general_styles import apply_label_style

class ClientsWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("👥 Клиенты")
        apply_label_style(title, 'h2')
        layout.addWidget(title)
        layout.addWidget(QTextEdit("Поиск, карточки клиентов, история, контакты, договоры."))
