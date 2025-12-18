"""
Диалог для редактирования веса товара
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt
from modules.styles.general_styles import (
    apply_label_style, apply_input_style, apply_button_style
)
from modules.styles.kp_styles import apply_kp_dialog_style


class WeightEditDialog(QDialog):
    """Диалог для редактирования веса товара"""
    
    def __init__(self, current_weight: float = 0.0, product_name: str = "", parent=None):
        """
        Инициализация диалога
        
        Args:
            current_weight: Текущий вес товара
            product_name: Название товара
            parent: Родительский виджет
        """
        super().__init__(parent)
        from modules.styles.ui_config import configure_dialog
        configure_dialog(self, "Редактирование веса товара", size_preset="small", min_width=350)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Информация о товаре
        if product_name:
            product_label = QLabel(f"Товар: {product_name}")
            apply_label_style(product_label, 'h3')
            layout.addWidget(product_label)
        
        # Поле для ввода веса
        weight_layout = QHBoxLayout()
        weight_label = QLabel("Вес (кг):")
        apply_label_style(weight_label, 'normal')
        weight_layout.addWidget(weight_label)
        
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setMinimum(0.01)
        self.weight_input.setMaximum(999999.99)
        self.weight_input.setDecimals(2)
        # Безопасное преобразование веса в число
        try:
            if isinstance(current_weight, str):
                weight_value = float(current_weight) if current_weight.strip() and current_weight != "-" else 1.0
            else:
                weight_value = float(current_weight) if current_weight and current_weight > 0 else 1.0
        except (ValueError, TypeError):
            weight_value = 1.0
        self.weight_input.setValue(weight_value)
        self.weight_input.selectAll()
        apply_input_style(self.weight_input)
        weight_layout.addWidget(self.weight_input)
        weight_layout.addStretch()
        layout.addLayout(weight_layout)
        
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
        weight = self.weight_input.value()
        if weight <= 0:
            QMessageBox.warning(
                self, "Ошибка",
                "Вес должен быть больше нуля"
            )
            return
        self.accept()
    
    def get_weight(self) -> float:
        """Получение введенного веса"""
        return self.weight_input.value()

