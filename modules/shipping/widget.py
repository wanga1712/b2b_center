from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from modules.styles.general_styles import apply_label_style

class ShippingWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("🚚 Отгрузка")
        apply_label_style(title, 'h2')
        layout.addWidget(title)
        layout.addWidget(QTextEdit("Интерфейс для управления отгрузками, расчёт логистики, печать документов."))
