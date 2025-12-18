"""
Модуль для управления стоп-словами в настройках.
"""

import re
from PyQt5.QtWidgets import QMessageBox
from loguru import logger

from services.tender_repository import TenderRepository


class StopWordsManager:
    """Класс для управления стоп-словами"""
    
    def __init__(self, tender_repo: TenderRepository, user_id: int):
        """
        Инициализация менеджера стоп-слов
        
        Args:
            tender_repo: Репозиторий для работы с тендерами
            user_id: ID пользователя
        """
        self.tender_repo = tender_repo
        self.user_id = user_id
    
    def add_stop_words(self, input_text: str, parent_widget=None):
        """Обработка добавления стоп-слов"""
        if not self.tender_repo:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", "Нет подключения к базе данных")
            return
        
        input_text = input_text.strip()
        if not input_text:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Предупреждение", "Введите стоп-слово или несколько слов")
            return
        
        # Разбиваем введенный текст на отдельные слова
        words = re.split(r'[,;\n\r]+', input_text)
        words = [word.strip() for word in words if word.strip()]
        
        if not words:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Предупреждение", "Не удалось извлечь стоп-слова из введенного текста")
            return
        
        # Проверяем, какие слова уже существуют в БД
        existing_words = []
        all_stop_words = self.tender_repo.get_user_stop_words(self.user_id)
        existing_words_set = {sw.get('stop_word', '').lower() for sw in all_stop_words}
        
        for word in words:
            if word.lower() in existing_words_set:
                existing_words.append(word)
        
        # Если все слова уже существуют, показываем предупреждение
        if len(existing_words) == len(words):
            existing_text = ", ".join(existing_words)
            QMessageBox.warning(
                parent_widget, 
                "Слово уже добавлено", 
                f"Все введенные слова уже используются:\n{existing_text}"
            )
            return
        
        # Показываем предупреждение, если некоторые слова уже существуют
        new_words = [w for w in words if w.lower() not in existing_words_set]
        if existing_words and new_words:
            existing_text = ", ".join(existing_words)
            QMessageBox.warning(
                parent_widget,
                "Часть слов уже добавлена",
                f"Следующие слова уже используются и не будут добавлены:\n{existing_text}\n\nБудут добавлены только новые слова."
            )
        
        # Добавляем только новые стоп-слова в БД
        result = self.tender_repo.add_user_stop_words(
            user_id=self.user_id,
            stop_words=new_words
        )
        
        # Формируем сообщение о результате
        if parent_widget:
            if result['added'] > 0:
                QMessageBox.information(parent_widget, "Успех", f"Добавлено слов: {result['added']}")
            elif result['errors']:
                error_msg = "\n".join(result['errors'][:3])  # Показываем только первые 3 ошибки
                QMessageBox.warning(parent_widget, "Ошибка", f"Ошибки при добавлении:\n{error_msg}")
    
    def remove_stop_word(self, stop_word_id: int, parent_widget=None):
        """Обработка удаления стоп-слова (без подтверждения - удаляет сразу)"""
        if not self.tender_repo:
            return
        
        # Удаляем сразу без диалога подтверждения
        success = self.tender_repo.remove_user_stop_word(self.user_id, stop_word_id)
        if not success and parent_widget:
            QMessageBox.warning(parent_widget, "Ошибка", "Не удалось удалить стоп-слово")

