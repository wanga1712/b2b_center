from ui.main_window import MainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
import sys
import os

if __name__ == "__main__":
    # ВКЛЮЧАЕМ ВЫСОКИЙ DPI SCALING ПЕРВЫМ ДЕЛОМ
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Создаем приложение
    app = QApplication(sys.argv)

    # Дополнительные настройки для высокого DPI
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Устанавливаем переменные окружения для Qt
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_SCALE_FACTOR"] = "1"  # Можно попробовать 1.25, 1.5 и т.д.

    # Создаем и показываем главное окно
    win = MainWindow()
    win.show()

    sys.exit(app.exec_())