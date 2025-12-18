"""
Диалог для редактирования единицы измерения товара
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt
from modules.styles.general_styles import (
    apply_label_style, apply_input_style, apply_button_style
)
from modules.styles.kp_styles import apply_kp_dialog_style


class UnitEditDialog(QDialog):
    """Диалог для редактирования единицы измерения товара"""
    
    def __init__(self, current_container_type: str = "", current_size: str = "", product_name: str = "", parent=None):
        """
        Инициализация диалога
        
        Args:
            current_container_type: Текущий тип тары (мешок, бочка и т.д.)
            current_size: Текущий размер упаковки
            product_name: Название товара
            parent: Родительский виджет
        """
        super().__init__(parent)
        from modules.styles.ui_config import configure_dialog
        configure_dialog(self, "Редактирование единицы измерения", size_preset="small", min_width=400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Информация о товаре
        if product_name:
            product_label = QLabel(f"Товар: {product_name}")
            apply_label_style(product_label, 'h3')
            layout.addWidget(product_label)
        
        # Поле для ввода типа тары
        container_layout = QHBoxLayout()
        container_label = QLabel("Тип тары:")
        apply_label_style(container_label, 'normal')
        container_layout.addWidget(container_label)
        
        self.container_input = QLineEdit()
        self.container_input.setText(current_container_type or "")
        self.container_input.setPlaceholderText("Например: мешок, бочка, ведро")
        apply_input_style(self.container_input)
        container_layout.addWidget(self.container_input)
        layout.addLayout(container_layout)
        
        # Поле для ввода размера
        size_layout = QHBoxLayout()
        size_label = QLabel("Размер:")
        apply_label_style(size_label, 'normal')
        size_layout.addWidget(size_label)
        
        self.size_input = QLineEdit()
        self.size_input.setText(current_size or "")
        self.size_input.setPlaceholderText("Например: 20л, 25кг")
        apply_input_style(self.size_input)
        size_layout.addWidget(self.size_input)
        layout.addLayout(size_layout)
        
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
        apply_kp_dialog_style(self)
    
    def validate_and_accept(self):
        """Валидация и принятие изменений"""
        # Можно оставить пустым, но хотя бы одно поле должно быть заполнено
        container = self.container_input.text().strip()
        size = self.size_input.text().strip()
        
        if not container and not size:
            QMessageBox.warning(
                self, "Ошибка",
                "Необходимо заполнить хотя бы одно поле (Тип тары или Размер)"
            )
            return
        self.accept()
    
    def get_container_type(self) -> str:
        """Получение введенного типа тары"""
        return self.container_input.text().strip()
    
    def get_size(self) -> str:
        """Получение введенного размера"""
        return self.size_input.text().strip()

