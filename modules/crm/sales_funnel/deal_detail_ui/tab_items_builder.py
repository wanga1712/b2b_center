"""
MODULE: modules.crm.sales_funnel.deal_detail_ui.tab_items_builder
RESPONSIBILITY: UI Builder for the "Items" tab (Products/Materials/Works) in Deal Detail dialog.
ALLOWED: PyQt5, modules.styles.general_styles.
FORBIDDEN: Business logic, Direct DB access.
ERRORS: None.

UI билдер для вкладки "КП / Товары" детальной карточки сделки.

Создает все таблицы: товары КП, материалы, работы.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
                             QPushButton, QScrollArea)
from PyQt5.QtCore import Qt

from modules.styles.general_styles import apply_button_style, apply_label_style, COLORS


class ItemsTabBuilder:
    """Класс для построения вкладки 'КП / Товары'."""
    
    @staticmethod
    def build_items_tab(tab_widget: QWidget) -> dict:
        """
        Построение вкладки 'КП / Товары'.
        
        Returns:
            dict с виджетами таблиц и меток для последующего использования
        """
        # Создаем скроллируемый контейнер
        items_scroll_area = QScrollArea(tab_widget)
        items_scroll_area.setWidgetResizable(True)
        items_scroll_area.setFrameShape(QScrollArea.NoFrame)
        
        items_content_widget = QWidget()
        layout = QVBoxLayout(items_content_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Устанавливаем скролл как основной виджет вкладки
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(items_scroll_area)
        
        widgets = {}
        
        # Раздел 0: Товары из базы данных
        widgets.update(ItemsTabBuilder._build_products_section(layout))
        
        # Раздел 1: Материалы
        widgets.update(ItemsTabBuilder._build_materials_section(layout))
        
        # Раздел 2: Работы
        widgets.update(ItemsTabBuilder._build_works_section(layout))
        
        # Растяжка
        layout.addStretch()
        
        # Устанавливаем контент в скролл
        items_scroll_area.setWidget(items_content_widget)
        
        return widgets
    
    @staticmethod
    def _build_products_section(parent_layout: QVBoxLayout) -> dict:
        """Построение секции товаров КП."""
        products_label = ItemsTabBuilder._make_section_label("🛒 Коммерческое предложение (товары из базы данных)")
        parent_layout.addWidget(products_label)
        
        # Контейнер
        products_container = QWidget()
        products_layout = QHBoxLayout(products_container)
        products_layout.setContentsMargins(0, 0, 0, 0)
        
        # Таблица товаров
        products_table = QTableWidget()
        products_table.setColumnCount(6)
        products_table.setHorizontalHeaderLabels(
            ["Наименование (начните вводить для поиска)", "Производитель", "Кол-во", "Ед.", "Цена за ед.", "Итого"]
        )
        products_table.horizontalHeader().setStretchLastSection(False)
        products_table.setColumnWidth(0, 300)
        products_table.setColumnWidth(1, 150)
        products_table.setColumnWidth(2, 80)
        products_table.setColumnWidth(3, 60)
        products_table.setColumnWidth(4, 100)
        products_table.setColumnWidth(5, 100)
        products_table.setEditTriggers(QTableWidget.AllEditTriggers)
        products_layout.addWidget(products_table, 3)
        
        # Блок итогов
        products_totals = QWidget()
        products_totals.setMaximumWidth(250)
        products_totals_layout = QVBoxLayout(products_totals)
        products_totals_layout.setContentsMargins(10, 10, 10, 10)
        products_totals_layout.setSpacing(10)
        
        totals_label_products = QLabel("<b>Итоги и сравнение:</b>")
        products_totals_layout.addWidget(totals_label_products)
        
        products_total_label = QLabel("Итого по КП:\n0.00 руб.")
        products_total_label.setStyleSheet(f"font-size: 14px; color: {COLORS['primary']}; font-weight: bold;")
        products_totals_layout.addWidget(products_total_label)
        
        comparison_label = QLabel("Сравнение со сметой:\n—")
        comparison_label.setStyleSheet("font-size: 12px; padding: 10px; border-radius: 5px; background-color: #f0f0f0;")
        comparison_label.setWordWrap(True)
        products_totals_layout.addWidget(comparison_label)
        
        add_product_btn = QPushButton("➕ Добавить товар")
        apply_button_style(add_product_btn, "secondary")
        products_totals_layout.addWidget(add_product_btn)
        
        save_products_btn = QPushButton("💾 Сохранить КП")
        apply_button_style(save_products_btn, "primary")
        products_totals_layout.addWidget(save_products_btn)
        
        products_totals_layout.addStretch()
        products_layout.addWidget(products_totals, 1)
        
        parent_layout.addWidget(products_container)
        
        return {
            'products_table': products_table,
            'products_total_label': products_total_label,
            'comparison_label': comparison_label,
            'add_product_btn': add_product_btn,
            'save_products_btn': save_products_btn,
        }
    
    @staticmethod
    def _build_materials_section(parent_layout: QVBoxLayout) -> dict:
        """Построение секции материалов."""
        materials_label = ItemsTabBuilder._make_section_label("📦 Материалы из проектной документации")
        parent_layout.addWidget(materials_label)
        
        # Контейнер
        materials_container = QWidget()
        materials_layout = QHBoxLayout(materials_container)
        materials_layout.setContentsMargins(0, 0, 0, 0)
        
        # Таблица материалов
        materials_table = QTableWidget()
        materials_table.setColumnCount(5)
        materials_table.setHorizontalHeaderLabels(
            ["Наименование", "Кол-во", "Ед.", "Цена за ед.", "Итого"]
        )
        materials_table.horizontalHeader().setStretchLastSection(False)
        materials_table.setColumnWidth(0, 300)
        materials_table.setColumnWidth(1, 80)
        materials_table.setColumnWidth(2, 60)
        materials_table.setColumnWidth(3, 100)
        materials_table.setColumnWidth(4, 100)
        materials_table.setEditTriggers(QTableWidget.AllEditTriggers)
        materials_layout.addWidget(materials_table, 3)
        
        # Блок итогов
        materials_totals = QWidget()
        materials_totals.setMaximumWidth(200)
        materials_totals_layout = QVBoxLayout(materials_totals)
        materials_totals_layout.setContentsMargins(10, 10, 10, 10)
        materials_totals_layout.setSpacing(10)
        
        totals_label = QLabel("<b>Итоги:</b>")
        materials_totals_layout.addWidget(totals_label)
        
        materials_total_label = QLabel("Итого по материалам:\n0.00 руб.")
        materials_total_label.setStyleSheet(f"font-size: 14px; color: {COLORS['primary']}; font-weight: bold;")
        materials_totals_layout.addWidget(materials_total_label)
        
        add_material_btn = QPushButton("➕ Добавить строку")
        apply_button_style(add_material_btn, "secondary")
        materials_totals_layout.addWidget(add_material_btn)
        
        save_materials_btn = QPushButton("💾 Сохранить материалы")
        apply_button_style(save_materials_btn, "primary")
        materials_totals_layout.addWidget(save_materials_btn)
        
        materials_totals_layout.addStretch()
        materials_layout.addWidget(materials_totals, 1)
        
        parent_layout.addWidget(materials_container)
        
        return {
            'materials_table': materials_table,
            'materials_total_label': materials_total_label,
            'add_material_btn': add_material_btn,
            'save_materials_btn': save_materials_btn,
        }
    
    @staticmethod
    def _build_works_section(parent_layout: QVBoxLayout) -> dict:
        """Построение секции работ."""
        works_label = ItemsTabBuilder._make_section_label("🛠 Работы из проектной документации")
        parent_layout.addWidget(works_label)
        
        # Контейнер
        works_container = QWidget()
        works_layout = QHBoxLayout(works_container)
        works_layout.setContentsMargins(0, 0, 0, 0)
        
        # Таблица работ
        works_table = QTableWidget()
        works_table.setColumnCount(5)
        works_table.setHorizontalHeaderLabels(
            ["Наименование", "Объем", "Ед.", "Цена за ед.", "Итого"]
        )
        works_table.horizontalHeader().setStretchLastSection(False)
        works_table.setColumnWidth(0, 300)
        works_table.setColumnWidth(1, 80)
        works_table.setColumnWidth(2, 60)
        works_table.setColumnWidth(3, 100)
        works_table.setColumnWidth(4, 100)
        works_table.setEditTriggers(QTableWidget.AllEditTriggers)
        works_layout.addWidget(works_table, 3)
        
        # Блок итогов
        works_totals = QWidget()
        works_totals.setMaximumWidth(200)
        works_totals_layout = QVBoxLayout(works_totals)
        works_totals_layout.setContentsMargins(10, 10, 10, 10)
        works_totals_layout.setSpacing(10)
        
        works_totals_label = QLabel("<b>Итоги:</b>")
        works_totals_layout.addWidget(works_totals_label)
        
        works_total_label = QLabel("Итого по работам:\n0.00 руб.")
        works_total_label.setStyleSheet(f"font-size: 14px; color: {COLORS['primary']}; font-weight: bold;")
        works_totals_layout.addWidget(works_total_label)
        
        add_work_btn = QPushButton("➕ Добавить строку")
        apply_button_style(add_work_btn, "secondary")
        works_totals_layout.addWidget(add_work_btn)
        
        save_works_btn = QPushButton("💾 Сохранить работы")
        apply_button_style(save_works_btn, "primary")
        works_totals_layout.addWidget(save_works_btn)
        
        works_totals_layout.addStretch()
        works_layout.addWidget(works_totals, 1)
        
        parent_layout.addWidget(works_container)
        
        return {
            'works_table': works_table,
            'works_total_label': works_total_label,
            'add_work_btn': add_work_btn,
            'save_works_btn': save_works_btn,
        }
    
    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        """Создание заголовка секции."""
        label = QLabel(text)
        apply_label_style(label, "h3")
        return label

