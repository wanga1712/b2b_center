"""
Диалог выбора воронки продаж для перемещения закупки
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QButtonGroup, QRadioButton
)
from PyQt5.QtCore import Qt
from modules.styles.general_styles import apply_label_style, apply_button_style, COLORS, SIZES
from modules.styles.ui_config import configure_dialog
from modules.crm.sales_funnel.models import PipelineType


class PipelineSelectionDialog(QDialog):
    """Диалог выбора воронки продаж"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_pipeline = None
        self.button_group = QButtonGroup(self)
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса диалога"""
        configure_dialog(self, "Выбор воронки продаж", 500, 400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Заголовок
        header = QLabel("Выберите воронку продаж для перемещения закупки:")
        apply_label_style(header, 'h2')
        header.setStyleSheet(f"color: {COLORS['text_dark']}; margin-bottom: 20px;")
        layout.addWidget(header)
        
        # Радио-кнопки для выбора воронки
        pipelines = [
            (PipelineType.PARTICIPATION, "🎯 Участвовать", "Участие в торгах"),
            (PipelineType.MATERIALS_SUPPLY, "📦 Поставка материалов", "Поставка материалов"),
            (PipelineType.SUBCONTRACTING, "🔧 Суб-подрядные работы", "Субподрядные работы"),
        ]
        
        # Сохраняем маппинг ID -> PipelineType
        self.pipeline_id_map = {}
        
        for idx, (pipeline_type, icon_name, description) in enumerate(pipelines):
            radio = QRadioButton(f"{icon_name} {description}")
            radio.setStyleSheet(f"""
                QRadioButton {{
                    font-size: 14px;
                    padding: 10px;
                    margin: 5px;
                }}
                QRadioButton:hover {{
                    background-color: {COLORS['secondary']};
                }}
            """)
            # Используем числовой ID (индекс)
            self.button_group.addButton(radio, idx)
            self.pipeline_id_map[idx] = pipeline_type
            layout.addWidget(radio)
        
        # Выбираем первую воронку по умолчанию
        if self.button_group.buttons():
            self.button_group.buttons()[0].setChecked(True)
        
        layout.addStretch()
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        btn_cancel = QPushButton("Отмена")
        apply_button_style(btn_cancel, 'outline')
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)
        
        btn_move = QPushButton("Переместить")
        apply_button_style(btn_move, 'primary')
        btn_move.clicked.connect(self.accept_selection)
        buttons_layout.addWidget(btn_move)
        
        layout.addLayout(buttons_layout)
    
    def accept_selection(self):
        """Обработка выбора воронки"""
        checked_button = self.button_group.checkedButton()
        if checked_button:
            button_id = self.button_group.id(checked_button)
            # Получаем PipelineType из маппинга
            self.selected_pipeline = self.pipeline_id_map.get(button_id)
            if self.selected_pipeline:
                self.accept()
            else:
                self.reject()
        else:
            self.reject()
    
    def get_selected_pipeline(self) -> PipelineType:
        """Получение выбранной воронки"""
        return self.selected_pipeline

