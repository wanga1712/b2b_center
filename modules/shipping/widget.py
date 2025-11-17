from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

class ShippingWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("🚚 Отгрузка")
        title.setStyleSheet("font-size:22px; margin-bottom:14px;")
        layout.addWidget(title)
        layout.addWidget(QTextEdit("Интерфейс для управления отгрузками, расчёт логистики, печать документов."))
