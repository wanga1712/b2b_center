"""
Глобальное масштабирование для всего приложения на основе физического размера экрана и DPI
"""
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings

class GlobalScaling:
    """Класс для глобального масштабирования интерфейса"""

    _instance = None
    _scale_factor = 1.0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalScaling, cls).__new__(cls)
            cls._instance._calculate_scale_factor()
        return cls._instance

    def _calculate_scale_factor(self):
        """Рассчитывает коэффициент масштабирования на основе физического размера экрана и DPI"""
        try:
            app = QApplication.instance()
            if not app:
                self._scale_factor = 1.0
                return

            screen = app.primaryScreen()
            if not screen:
                self._scale_factor = 1.0
                return

            # Получаем физический размер экрана в мм
            physical_size = screen.physicalSize()
            if physical_size.isValid():
                # Рассчитываем диагональ в дюймах
                width_inch = physical_size.width() / 25.4
                height_inch = physical_size.height() / 25.4
                diagonal = (width_inch ** 2 + height_inch ** 2) ** 0.5

                # Получаем логическое разрешение
                screen_rect = screen.availableGeometry()
                screen_width = screen_rect.width()
                screen_height = screen_rect.height()
                
                # Рассчитываем DPI на основе физического размера и логического разрешения
                dpi_x = screen_width / width_inch if width_inch > 0 else 96
                dpi_y = screen_height / height_inch if height_inch > 0 else 96
                dpi = (dpi_x + dpi_y) / 2

                # Настраиваем масштабирование на основе диагонали и DPI
                # Для маленьких экранов с высоким DPI (ноутбуки) увеличиваем масштаб
                if diagonal <= 13:  # Маленькие ноутбуки 13"
                    self._scale_factor = 1.4
                elif diagonal <= 15:  # Стандартные ноутбуки 15"
                    # Для 15" ноутбуков учитываем DPI
                    if dpi > 130:
                        self._scale_factor = 1.3
                    else:
                        self._scale_factor = 1.2
                elif diagonal <= 17:  # Большие ноутбуки 17"
                    self._scale_factor = 1.2
                elif diagonal <= 21:  # Средние мониторы 21-22"
                    self._scale_factor = 1.1
                elif diagonal <= 24:  # Стандартные мониторы 24"
                    self._scale_factor = 1.0
                elif diagonal <= 27:  # Большие мониторы 27"
                    self._scale_factor = 0.95
                else:  # Очень большие мониторы 27"+
                    self._scale_factor = 0.9

                print(f"Обнаружена диагональ экрана: {diagonal:.1f}\", DPI: {dpi:.1f}, коэффициент масштабирования: {self._scale_factor}")
                return

            # Если не удалось получить физический размер, используем DPI и логическое разрешение
            dpi = screen.logicalDotsPerInch()
            screen_rect = screen.availableGeometry()
            screen_width = screen_rect.width()
            
            if dpi > 130:  # Высокий DPI (ноутбуки)
                # Дополнительно проверяем разрешение
                if screen_width <= 1366:
                    self._scale_factor = 1.4
                elif screen_width <= 1600:
                    self._scale_factor = 1.3
                else:
                    self._scale_factor = 1.2
            elif dpi > 110:  # Средний DPI
                self._scale_factor = 1.1
            else:  # Нормальный DPI
                self._scale_factor = 1.0

            print(f"Обнаружен DPI: {dpi:.1f}, разрешение: {screen_width}x{screen_rect.height()}, коэффициент масштабирования: {self._scale_factor}")

        except Exception as e:
            print(f"Ошибка расчета масштабирования: {e}")
            self._scale_factor = 1.0

    def get_scale_factor(self):
        """Возвращает коэффициент масштабирования"""
        return self._scale_factor

    def scale_size(self, size):
        """Масштабирует размер"""
        return int(size * self._scale_factor)

    def scale_font_size(self, base_size):
        """Масштабирует размер шрифта"""
        return self.scale_size(base_size)

# Глобальные функции для удобства
def get_scale_factor():
    return GlobalScaling().get_scale_factor()

def scale_size(size):
    return GlobalScaling().scale_size(size)

def scale_font_size(base_size):
    return GlobalScaling().scale_font_size(base_size)