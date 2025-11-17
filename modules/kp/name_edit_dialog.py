"""
Диалог для редактирования наименования товара
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt
from modules.styles.general_styles import (
    apply_label_style, apply_input_style, apply_button_style, COLORS
)


class NameEditDialog(QDialog):
    """Диалог для редактирования наименования товара"""
    
    def __init__(self, current_name: str = "", parent=None):
        """
        Инициализация диалога
        
        Args:
            current_name: Текущее наименование товара
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.setWindowTitle("Редактирование наименования товара")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Поле для ввода наименования
        name_layout = QHBoxLayout()
        name_label = QLabel("Наименование:")
        apply_label_style(name_label, 'normal')
        name_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setText(current_name)
        self.name_input.selectAll()
        apply_input_style(self.name_input)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Кнопки
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        
        # Применяем стили к кнопкам
        ok_button = button_box.button(QDialogButtonBox.Ok)
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        apply_button_style(ok_button, 'primary')
        apply_button_style(cancel_button, 'outline')
        
        layout.addWidget(button_box)
        
        # Стиль диалога
        self.setStyleSheet(f"""
            QDialog {{
                background: {COLORS['white']};
            }}
        """)
    
    def validate_and_accept(self):
        """Валидация и принятие изменений"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Ошибка",
                "Наименование не может быть пустым"
            )
            return
        self.accept()
    
    def get_name(self) -> str:
        """Получение введенного наименования"""
        return self.name_input.text().strip()

