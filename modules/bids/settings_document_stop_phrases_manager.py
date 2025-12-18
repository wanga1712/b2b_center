"""
Модуль для управления стоп-фразами анализа документации в настройках.
"""

import re
from typing import List

from PyQt5.QtWidgets import QMessageBox
from loguru import logger

from services.tender_repository import TenderRepository


class DocumentStopPhrasesManager:
    """Класс для управления стоп-фразами анализа документации."""

    def __init__(self, tender_repo: TenderRepository, user_id: int):
        """
        Инициализация менеджера стоп-фраз.

        Args:
            tender_repo: Репозиторий для работы с тендерами.
            user_id: ID пользователя.
        """
        self.tender_repo = tender_repo
        self.user_id = user_id

    def _split_input(self, input_text: str) -> List[str]:
        """Разбиение ввода на отдельные фразы по запятым/переводам строки/точкам с запятой."""
        phrases = re.split(r"[,;\n\r]+", input_text)
        return [phrase.strip() for phrase in phrases if phrase.strip()]

    def add_stop_phrases(self, input_text: str, parent_widget=None) -> None:
        """Обработка добавления стоп-фраз."""
        if not self.tender_repo:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", "Нет подключения к базе данных")
            return

        input_text = input_text.strip()
        if not input_text:
            if parent_widget:
                QMessageBox.warning(
                    parent_widget,
                    "Предупреждение",
                    "Введите стоп-фразу или несколько фраз",
                )
            return

        phrases = self._split_input(input_text)
        if not phrases:
            if parent_widget:
                QMessageBox.warning(
                    parent_widget,
                    "Предупреждение",
                    "Не удалось извлечь стоп-фразы из введенного текста",
                )
            return

        # Проверяем существующие фразы
        existing_rows = self.tender_repo.get_document_stop_phrases(self.user_id)
        existing_set = {row.get("phrase", "").lower() for row in existing_rows}

        existing_phrases = [p for p in phrases if p.lower() in existing_set]
        if len(existing_phrases) == len(phrases):
            if parent_widget:
                QMessageBox.warning(
                    parent_widget,
                    "Фразы уже добавлены",
                    "Все введённые стоп-фразы уже есть в списке.",
                )
            return

        new_phrases = [p for p in phrases if p.lower() not in existing_set]
        if existing_phrases and new_phrases and parent_widget:
            QMessageBox.warning(
                parent_widget,
                "Часть фраз уже добавлена",
                "Некоторые введённые фразы уже существуют и не будут добавлены.\n"
                "Будут добавлены только новые фразы.",
            )

        result = self.tender_repo.add_document_stop_phrases(
            user_id=self.user_id,
            phrases=new_phrases,
        )

        if parent_widget:
            if result.get("added", 0) > 0:
                QMessageBox.information(
                    parent_widget,
                    "Успех",
                    f"Добавлено стоп-фраз: {result['added']}",
                )
            elif result.get("errors"):
                error_msg = "\n".join(result["errors"][:3])
                QMessageBox.warning(
                    parent_widget,
                    "Ошибка",
                    f"Ошибки при добавлении стоп-фраз:\n{error_msg}",
                )

    def remove_stop_phrase(self, phrase_id: int, parent_widget=None) -> None:
        """Удаление стоп-фразы."""
        if not self.tender_repo:
            return

        success = self.tender_repo.remove_document_stop_phrase(self.user_id, phrase_id)
        if not success and parent_widget:
            QMessageBox.warning(
                parent_widget,
                "Ошибка",
                "Не удалось удалить стоп-фразу",
            )


