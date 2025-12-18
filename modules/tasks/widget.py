from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QFrame,
    QGridLayout,
    QStackedWidget,
)

from modules.styles.general_styles import apply_label_style, apply_frame_style
from modules.travel_report.widget import TravelReportWidget


class TravelReportCard(QFrame):
    """Карточка-команда для перехода к отчету по командировке."""

    double_clicked = pyqtSignal()
    clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        apply_frame_style(self, "card")
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel("🧳")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 42px;")
        icon_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(icon_label)

        title_label = QLabel("Отчеты по командировкам")
        title_label.setAlignment(Qt.AlignCenter)
        apply_label_style(title_label, "h3")
        title_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(title_label)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        """Открытие отчета по двойному клику."""
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """Открытие отчета по одинарному клику (дополнительно к double-click)."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class TasksWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()

        main_layout = QVBoxLayout(self)

        title = QLabel("✅ Задачи")
        apply_label_style(title, "h2")
        main_layout.addWidget(title)

        main_layout.addWidget(
            QTextEdit(
                "Список задач, статусы, дедлайны, напоминания по процессам."
            )
        )

        self.stacked = QStackedWidget()
        main_layout.addWidget(self.stacked)

        # Страница с иконками/папками
        menu_page = QWidget()
        menu_layout = QGridLayout(menu_page)
        menu_layout.setContentsMargins(16, 16, 16, 16)
        menu_layout.setSpacing(16)

        travel_card = TravelReportCard(menu_page)
        travel_card.double_clicked.connect(self.show_travel_report)
        travel_card.clicked.connect(self.show_travel_report)
        menu_layout.addWidget(travel_card, 0, 0, alignment=Qt.AlignTop | Qt.AlignLeft)

        self.stacked.addWidget(menu_page)

        # Страница с самим отчетом по командировке
        self.travel_report_widget = TravelReportWidget(self)
        self.stacked.addWidget(self.travel_report_widget)

    def show_travel_report(self) -> None:
        """Переключение на страницу отчета по командировке."""
        self.stacked.setCurrentIndex(1)
