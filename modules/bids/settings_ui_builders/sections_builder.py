"""
UI билдер для всех секций настроек закупок.

Создает секции: фильтр категорий, ОКПД, категории, стоп-слова, документ стоп-фразы, кнопка показа.
"""

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QWidget
from PyQt5.QtCore import Qt

from modules.bids.salesforce_settings_ui import (
    create_salesforce_section_card, create_salesforce_input_row,
    create_salesforce_button, create_salesforce_list_widget
)


class SettingsSectionsBuilder:
    """Билдер для создания всех секций настроек закупок."""
    
    @staticmethod
    def build_category_filter_section(parent_layout: QVBoxLayout) -> dict:
        """Создание секции фильтрации по категории."""
        card = create_salesforce_section_card(
            title="🔍 Фильтрация по категории",
            description="Выберите категорию ОКПД для фильтрации закупок. Будут показаны только закупки с ОКПД кодами из выбранной категории."
        )
        card_layout = card.layout()
        
        category_filter_combo = QComboBox()
        category_filter_combo.setMinimumWidth(400)
        category_filter_combo.addItem("Все категории", None)
        
        input_row = create_salesforce_input_row(
            label_text="Категория",
            input_widget=category_filter_combo,
            help_text="Выберите категорию для фильтрации или 'Все категории' для отображения всех"
        )
        card_layout.addLayout(input_row)
        
        parent_layout.addWidget(card)
        
        return {'category_filter_combo': category_filter_combo}
    
    @staticmethod
    def build_okpd_section(parent_layout: QVBoxLayout) -> dict:
        """Создание секции выбора ОКПД."""
        card = create_salesforce_section_card(
            title="📋 Выбор кодов ОКПД",
            description="Выберите коды ОКПД для поиска закупок. Используйте поиск по коду или названию."
        )
        card_layout = card.layout()
        
        # Регион
        region_combo = QComboBox()
        region_combo.setMinimumWidth(400)
        region_row = create_salesforce_input_row(
            label_text="Регион",
            input_widget=region_combo,
            help_text="Выберите регион для поиска ОКПД кодов"
        )
        card_layout.addLayout(region_row)
        
        # Поиск ОКПД
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        
        okpd_search_input = QLineEdit()
        okpd_search_input.setPlaceholderText("Введите код ОКПД или название для поиска...")
        search_layout.addWidget(okpd_search_input, 3)
        
        btn_add_okpd = create_salesforce_button("+ Добавить", 'primary')
        search_layout.addWidget(btn_add_okpd, 1)
        
        search_row = create_salesforce_input_row(
            label_text="Поиск ОКПД",
            input_widget=QWidget(),  # Placeholder
            help_text="Введите код или название, затем нажмите 'Добавить'"
        )
        search_row.takeAt(1)  # Удаляем placeholder
        search_row.addLayout(search_layout)
        card_layout.addLayout(search_row)
        
        # Список результатов
        from modules.styles.general_styles import FONT_SIZES, COLORS
        from PyQt5.QtWidgets import QLabel
        
        results_label = QLabel("Доступные коды ОКПД:")
        results_label.setStyleSheet(f"font-size: {FONT_SIZES['normal']}; font-weight: 600; color: {COLORS['text_dark']};")
        card_layout.addWidget(results_label)
        
        okpd_results_list = create_salesforce_list_widget()
        okpd_results_list.setMinimumHeight(300)
        okpd_results_list.setMaximumHeight(400)
        card_layout.addWidget(okpd_results_list)
        
        parent_layout.addWidget(card)
        
        return {
            'region_combo': region_combo,
            'okpd_search_input': okpd_search_input,
            'btn_add_okpd': btn_add_okpd,
            'okpd_results_list': okpd_results_list,
        }
    
    @staticmethod
    def build_categories_section(parent_layout: QVBoxLayout) -> dict:
        """Создание секции управления категориями."""
        card = create_salesforce_section_card(
            title="📂 Управление категориями ОКПД",
            description="Создавайте категории для группировки ОКПД кодов и назначайте коды в категории."
        )
        card_layout = card.layout()
        
        # Список категорий и кнопки управления
        from PyQt5.QtWidgets import QLabel
        from modules.styles.general_styles import FONT_SIZES, COLORS
        
        categories_label = QLabel("Ваши категории:")
        categories_label.setStyleSheet(f"font-size: {FONT_SIZES['normal']}; font-weight: 600; color: {COLORS['text_dark']};")
        card_layout.addWidget(categories_label)
        
        categories_list = create_salesforce_list_widget()
        categories_list.setMinimumHeight(200)
        categories_list.setMaximumHeight(300)
        card_layout.addWidget(categories_list)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        btn_create_category = create_salesforce_button("+ Создать", 'primary')
        buttons_layout.addWidget(btn_create_category)
        
        btn_rename_category = create_salesforce_button("✏️ Переименовать", 'outline')
        buttons_layout.addWidget(btn_rename_category)
        
        btn_delete_category = create_salesforce_button("🗑️ Удалить", 'outline')
        buttons_layout.addWidget(btn_delete_category)
        
        btn_assign_category = create_salesforce_button("📂 Назначить категорию", 'outline')
        buttons_layout.addWidget(btn_assign_category)
        
        buttons_layout.addStretch()
        card_layout.addLayout(buttons_layout)
        
        parent_layout.addWidget(card)
        
        return {
            'categories_list': categories_list,
            'btn_create_category': btn_create_category,
            'btn_rename_category': btn_rename_category,
            'btn_delete_category': btn_delete_category,
            'btn_assign_category': btn_assign_category,
        }
    
    @staticmethod
    def build_added_okpd_section(parent_layout: QVBoxLayout) -> dict:
        """Создание секции добавленных ОКПД."""
        from PyQt5.QtWidgets import QScrollArea
        from modules.styles.general_styles import COLORS, SIZES
        
        card = create_salesforce_section_card(
            title="✅ Добавленные ОКПД",
            description="Список ОКПД кодов, которые используются для поиска закупок. Вы можете назначить категорию или удалить код."
        )
        card_layout = card.layout()
        
        # Контейнер для добавленных ОКПД (используется в load_user_okpd_codes)
        added_okpd_container = QWidget()
        added_okpd_layout = QVBoxLayout(added_okpd_container)
        added_okpd_layout.setSpacing(8)
        added_okpd_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(added_okpd_container)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMaximumHeight(350)
        scroll_area.setStyleSheet(
            f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_small']}px;
                background: {COLORS['white']};
            }}
            """
        )
        card_layout.addWidget(scroll_area)
        
        parent_layout.addWidget(card)
        
        return {
            'added_okpd_container': added_okpd_container,
            'added_okpd_layout': added_okpd_layout
        }
    
    @staticmethod
    def build_stop_words_section(parent_layout: QVBoxLayout) -> dict:
        """Создание секции стоп-слов."""
        from PyQt5.QtWidgets import QScrollArea
        from modules.styles.general_styles import FONT_SIZES, COLORS, SIZES
        
        card = create_salesforce_section_card(
            title="🚫 Стоп-слова",
            description="Закупки, содержащие эти слова в названии, будут исключены из результатов."
        )
        card_layout = card.layout()
        
        # Поле ввода и кнопка
        add_layout = QHBoxLayout()
        add_layout.setSpacing(10)
        
        stop_word_input = QLineEdit()
        stop_word_input.setPlaceholderText("Введите стоп-слово...")
        add_layout.addWidget(stop_word_input, 3)
        
        btn_add_stop_word = create_salesforce_button("+ Добавить", 'primary')
        add_layout.addWidget(btn_add_stop_word, 1)
        
        card_layout.addLayout(add_layout)
        
        # Контейнер для стоп-слов (используется в load_user_stop_words)
        from PyQt5.QtWidgets import QLabel
        stopwords_label = QLabel("Активные стоп-слова:")
        stopwords_label.setStyleSheet(f"font-size: {FONT_SIZES['normal']}; font-weight: 600; color: {COLORS['text_dark']};")
        card_layout.addWidget(stopwords_label)
        
        stop_words_container = QWidget()
        stop_words_layout = QVBoxLayout(stop_words_container)
        stop_words_layout.setContentsMargins(0, 0, 0, 0)
        stop_words_layout.setSpacing(8)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(stop_words_container)
        scroll_area.setMinimumHeight(150)
        scroll_area.setMaximumHeight(250)
        scroll_area.setStyleSheet(
            f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_small']}px;
                background: {COLORS['white']};
            }}
            """
        )
        card_layout.addWidget(scroll_area)
        
        parent_layout.addWidget(card)
        
        return {
            'stop_word_input': stop_word_input,
            'btn_add_stop_word': btn_add_stop_word,
            'stop_words_container': stop_words_container,
            'stop_words_layout': stop_words_layout,
        }
    
    @staticmethod
    def build_document_stop_phrases_section(parent_layout: QVBoxLayout) -> dict:
        """Создание секции стоп-фраз для документов."""
        from PyQt5.QtWidgets import QScrollArea
        from modules.styles.general_styles import FONT_SIZES, COLORS, SIZES
        
        card = create_salesforce_section_card(
            title="📄 Стоп-фразы документации",
            description="Фразы для исключения закупок при анализе документации."
        )
        card_layout = card.layout()
        
        # Поле ввода и кнопка
        add_layout = QHBoxLayout()
        add_layout.setSpacing(10)
        
        document_stop_phrase_input = QLineEdit()
        document_stop_phrase_input.setPlaceholderText("Введите стоп-фразу...")
        add_layout.addWidget(document_stop_phrase_input, 3)
        
        btn_add_phrase = create_salesforce_button("+ Добавить", 'primary')
        add_layout.addWidget(btn_add_phrase, 1)
        
        card_layout.addLayout(add_layout)
        
        # Контейнер для стоп-фраз (используется в load_document_stop_phrases)
        from PyQt5.QtWidgets import QLabel
        phrases_label = QLabel("Активные стоп-фразы:")
        phrases_label.setStyleSheet(f"font-size: {FONT_SIZES['normal']}; font-weight: 600; color: {COLORS['text_dark']};")
        card_layout.addWidget(phrases_label)
        
        document_stop_phrases_container = QWidget()
        document_stop_phrases_layout = QVBoxLayout(document_stop_phrases_container)
        document_stop_phrases_layout.setContentsMargins(0, 0, 0, 0)
        document_stop_phrases_layout.setSpacing(8)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(document_stop_phrases_container)
        scroll_area.setMinimumHeight(150)
        scroll_area.setMaximumHeight(250)
        scroll_area.setStyleSheet(
            f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: {SIZES['border_radius_small']}px;
                background: {COLORS['white']};
            }}
            """
        )
        card_layout.addWidget(scroll_area)
        
        parent_layout.addWidget(card)
        
        return {
            'document_stop_phrase_input': document_stop_phrase_input,
            'btn_add_phrase': btn_add_phrase,
            'document_stop_phrases_container': document_stop_phrases_container,
            'document_stop_phrases_layout': document_stop_phrases_layout,
        }
    
    @staticmethod
    def build_show_tenders_section(parent_layout: QVBoxLayout) -> dict:
        """Создание секции кнопок применения настроек."""
        from modules.bids.salesforce_settings_ui import create_salesforce_button
        
        card = create_salesforce_section_card(
            title="🎯 Применить настройки",
            description="Обновите данные или сохраните настройки для постоянного использования."
        )
        card_layout = card.layout()
        
        # Горизонтальный layout для кнопок
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        btn_update_data = create_salesforce_button("🔄 Обновить данные", 'primary')
        buttons_layout.addWidget(btn_update_data)
        
        btn_save_settings = create_salesforce_button("💾 Сохранить настройки", 'success')
        buttons_layout.addWidget(btn_save_settings)
        
        btn_back = create_salesforce_button("← Назад к дашборду", 'outline')
        buttons_layout.addWidget(btn_back)
        
        buttons_layout.addStretch()
        
        card_layout.addLayout(buttons_layout)
        
        parent_layout.addWidget(card)
        
        return {
            'btn_update_data': btn_update_data,
            'btn_save_settings': btn_save_settings,
            'btn_back': btn_back
        }

