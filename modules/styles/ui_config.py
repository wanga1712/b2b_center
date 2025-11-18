"""
Централизованная конфигурация UI для PyQt5.

Содержит функции для настройки окон, диалогов, размеров и расположения элементов.
Все настройки UI должны использовать функции из этого модуля.
"""

from typing import Optional, Tuple
from PyQt5.QtWidgets import QDialog, QMainWindow, QWidget
from PyQt5.QtCore import Qt

from modules.styles.general_styles import COLORS, SIZES


class WindowConfig:
    """Класс для конфигурации окон и диалогов."""

    # Стандартные размеры окон
    DIALOG_SIZES = {
        "small": (400, 300),
        "medium": (600, 400),
        "large": (800, 600),
        "xlarge": (1000, 700),
        "result_dialog": (820, 640),
        "progress_dialog": (500, 200),
        "ai_chat": (700, 600),
        "tender_detail": (800, 600),
    }

    # Стандартные минимальные размеры
    MIN_SIZES = {
        "dialog": (400, 300),
        "window": (800, 600),
        "tender_detail": (800, 600),
    }

    @staticmethod
    def configure_dialog(
        dialog: QDialog,
        title: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        size_preset: Optional[str] = None,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
    ) -> None:
        """
        Настройка диалогового окна.
        
        Args:
            dialog: Экземпляр QDialog
            title: Заголовок окна
            width: Ширина окна (если не указан, используется size_preset)
            height: Высота окна (если не указан, используется size_preset)
            size_preset: Предустановленный размер ('small', 'medium', 'large', 'xlarge')
            min_width: Минимальная ширина
            min_height: Минимальная высота
        """
        dialog.setWindowTitle(title)
        
        if size_preset and size_preset in WindowConfig.DIALOG_SIZES:
            preset_width, preset_height = WindowConfig.DIALOG_SIZES[size_preset]
            width = width or preset_width
            height = height or preset_height
        
        if width and height:
            dialog.resize(width, height)
        
        # Устанавливаем минимальный размер
        if min_width and min_height:
            dialog.setMinimumSize(min_width, min_height)
        elif min_width:
            # Если указана только ширина, используем стандартную высоту
            min_w, min_h = WindowConfig.MIN_SIZES["dialog"]
            dialog.setMinimumSize(min_width, min_h)
        elif min_height:
            # Если указана только высота, используем стандартную ширину
            min_w, min_h = WindowConfig.MIN_SIZES["dialog"]
            dialog.setMinimumSize(min_w, min_height)
        else:
            # Устанавливаем минимальный размер по умолчанию
            min_w, min_h = WindowConfig.MIN_SIZES["dialog"]
            dialog.setMinimumSize(min_w, min_h)

    @staticmethod
    def configure_window(
        window: QMainWindow,
        title: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
    ) -> None:
        """
        Настройка главного окна приложения.
        
        Args:
            window: Экземпляр QMainWindow
            title: Заголовок окна
            width: Ширина окна
            height: Высота окна
            min_width: Минимальная ширина
            min_height: Минимальная высота
        """
        window.setWindowTitle(title)
        
        if width and height:
            window.resize(width, height)
        
        if min_width and min_height:
            window.setMinimumSize(min_width, min_height)
        else:
            min_w, min_h = WindowConfig.MIN_SIZES["window"]
            window.setMinimumSize(min_w, min_h)

    @staticmethod
    def set_dialog_size(
        dialog: QDialog,
        width: int,
        height: int,
    ) -> None:
        """Установка размера диалога."""
        dialog.resize(width, height)

    @staticmethod
    def set_window_size(
        window: QMainWindow,
        width: int,
        height: int,
    ) -> None:
        """Установка размера главного окна."""
        window.resize(width, height)

    @staticmethod
    def set_minimum_size(
        widget: QWidget,
        width: int,
        height: int,
    ) -> None:
        """Установка минимального размера виджета."""
        widget.setMinimumSize(width, height)

    @staticmethod
    def set_maximum_size(
        widget: QWidget,
        width: int,
        height: int,
    ) -> None:
        """Установка максимального размера виджета."""
        widget.setMaximumSize(width, height)


# Функции-обертки для удобства использования
def configure_dialog(
    dialog: QDialog,
    title: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    size_preset: Optional[str] = None,
    min_width: Optional[int] = None,
    min_height: Optional[int] = None,
) -> None:
    """Настройка диалогового окна."""
    WindowConfig.configure_dialog(
        dialog, title, width, height, size_preset, min_width, min_height
    )


def configure_window(
    window: QMainWindow,
    title: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    min_width: Optional[int] = None,
    min_height: Optional[int] = None,
) -> None:
    """Настройка главного окна приложения."""
    WindowConfig.configure_window(window, title, width, height, min_width, min_height)


def set_dialog_size(dialog: QDialog, width: int, height: int) -> None:
    """Установка размера диалога."""
    WindowConfig.set_dialog_size(dialog, width, height)


def set_window_size(window: QMainWindow, width: int, height: int) -> None:
    """Установка размера главного окна."""
    WindowConfig.set_window_size(window, width, height)


def set_minimum_size(widget: QWidget, width: int, height: int) -> None:
    """Установка минимального размера виджета."""
    WindowConfig.set_minimum_size(widget, width, height)


def set_maximum_size(widget: QWidget, width: int, height: int) -> None:
    """Установка максимального размера виджета."""
    WindowConfig.set_maximum_size(widget, width, height)

