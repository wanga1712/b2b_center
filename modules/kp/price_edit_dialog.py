"""
Диалог для редактирования цены товара
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt
from modules.styles.general_styles import (
    apply_label_style, apply_input_style, apply_button_style, COLORS
)


class PriceEditDialog(QDialog):
    """Диалог для редактирования цены товара"""
    
    def __init__(self, current_price: float = 0.0, product_name: str = "", parent=None):
        """
        Инициализация диалога
        
        Args:
            current_price: Текущая цена товара
            product_name: Название товара
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.setWindowTitle("Редактирование цены товара")
        self.setMinimumWidth(350)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Информация о товаре
        if product_name:
            product_label = QLabel(f"Товар: {product_name}")
            apply_label_style(product_label, 'h3')
            layout.addWidget(product_label)
        
        # Поле для ввода цены
        price_layout = QHBoxLayout()
        price_label = QLabel("Цена (₽):")
        apply_label_style(price_label, 'normal')
        price_layout.addWidget(price_label)
        
        self.price_input = QDoubleSpinBox()
        self.price_input.setMinimum(0.01)
        self.price_input.setMaximum(99999999.99)
        self.price_input.setDecimals(2)
        self.price_input.setValue(current_price if current_price > 0 else 1.0)
        self.price_input.selectAll()
        apply_input_style(self.price_input)
        price_layout.addWidget(self.price_input)
        price_layout.addStretch()
        layout.addLayout(price_layout)
        
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
        price = self.price_input.value()
        if price <= 0:
            QMessageBox.warning(
                self, "Ошибка",
                "Цена должна быть больше нуля"
            )
            return
        self.accept()
    
    def get_price(self) -> float:
        """Получение введенной цены"""
        return self.price_input.value()

