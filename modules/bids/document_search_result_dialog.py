from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QFrame,
    QHBoxLayout,
)
from PyQt5.QtGui import QDesktopServices
from loguru import logger

from modules.styles.general_styles import (
    apply_button_style,
    apply_frame_style,
    apply_label_style,
    COLORS,
    apply_text_style_light,
    apply_font_weight,
)
from modules.styles.ui_config import configure_dialog
from services.archive_processing_service import ArchiveProcessingService


class DocumentSearchResultDialog(QDialog):
    """Диалоговое окно с результатами поиска по документации."""

    def __init__(
        self,
        parent,
        grouped_matches: Dict[str, List[Dict[str, str]]],
        tender_folder: Path,
        download_root: Path,
    ):
        super().__init__(parent)
        configure_dialog(self, "Результаты поиска по документации", size_preset="result_dialog")
        self.tender_folder = tender_folder
        self.download_root = download_root
        self._init_ui(grouped_matches)

    def _init_ui(self, grouped_matches: Dict[str, List[Dict[str, str]]]) -> None:
        try:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)

            title = QLabel("🔍 Результаты анализа документов")
            apply_label_style(title, "h1")
            title.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(title)

            # Безопасное отображение пути к папке
            folder_text = f"📁 Папка: {self.tender_folder}"
            try:
                if not Path(self.tender_folder).exists():
                    folder_text += " (папка не найдена)"
            except Exception:
                pass
            
            folder_label = QLabel(folder_text)
            folder_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            apply_label_style(folder_label, "normal")
            layout.addWidget(folder_label)

            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            scroll_layout.setSpacing(12)
            scroll_layout.setContentsMargins(0, 0, 0, 0)

            # Безопасное получение групп совпадений
            exact_matches = grouped_matches.get("exact", [])
            good_matches = grouped_matches.get("good", [])
            
            if not isinstance(exact_matches, list):
                logger.warning(f"Неверный формат exact_matches: {type(exact_matches)}")
                exact_matches = []
            if not isinstance(good_matches, list):
                logger.warning(f"Неверный формат good_matches: {type(good_matches)}")
                good_matches = []

            try:
                self._add_group(scroll_layout, "✅ Точные совпадения", exact_matches)
                self._add_group(scroll_layout, "🔍 Хорошие совпадения", good_matches)
            except Exception as e:
                logger.error(f"Ошибка при добавлении групп совпадений: {e}", exc_info=True)

            if not exact_matches and not good_matches:
                empty_label = QLabel("Совпадений не найдено.")
                apply_label_style(empty_label, "normal")
                apply_text_style_light(empty_label)
                scroll_layout.addWidget(empty_label)

            scroll_area.setWidget(scroll_widget)
            layout.addWidget(scroll_area)

            button_row = QHBoxLayout()
            button_row.addStretch()

            btn_open_folder = QPushButton("📂 Открыть папку")
            apply_button_style(btn_open_folder, "outline")
            btn_open_folder.clicked.connect(self._handle_open_folder)
            button_row.addWidget(btn_open_folder)

            btn_close = QPushButton("Закрыть")
            apply_button_style(btn_close, "primary")
            btn_close.clicked.connect(self.accept)
            button_row.addWidget(btn_close)

            layout.addLayout(button_row)
        except Exception as e:
            logger.exception("Критическая ошибка при инициализации UI диалога результатов")
            raise

    def _add_group(self, parent_layout: QVBoxLayout, title: str, matches: List[Dict[str, str]]) -> None:
        if not matches:
            return

        group_label = QLabel(title)
        apply_label_style(group_label, "h2")
        parent_layout.addWidget(group_label)

        for match in matches:
            try:
                # Проверяем обязательные поля
                if not isinstance(match, dict):
                    continue
                
                product_name = match.get('product_name', 'Неизвестный товар')
                score = match.get('score', 0.0)
                try:
                    score = float(score)
                except (ValueError, TypeError):
                    score = 0.0
                
                # Безопасное получение chunk
                try:
                    chunk = ArchiveProcessingService.build_display_chunks(match, self.download_root)
                except Exception as e:
                    logger.error(f"Ошибка при построении chunk для {product_name}: {e}")
                    chunk = {
                        "file_info": "Ошибка обработки данных",
                        "summary": "",
                        "cell_text": ""
                    }
                
                frame = QFrame()
                apply_frame_style(frame, "content")
                frame_layout = QVBoxLayout(frame)
                frame_layout.setSpacing(6)

                header = QLabel(f"{product_name} • {score:.1f}%")
                header.setTextInteractionFlags(Qt.TextSelectableByMouse)
                apply_label_style(header, "normal")
                apply_font_weight(header)
                frame_layout.addWidget(header)

                file_info = chunk.get("file_info", "Информация о файле недоступна")
                file_label = QLabel(file_info)
                file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                apply_label_style(file_label, "small")
                frame_layout.addWidget(file_label)

                summary = chunk.get("summary", "")
                if summary:
                    summary_label = QLabel(summary)
                    summary_label.setWordWrap(True)
                    summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    apply_label_style(summary_label, "normal")
                    frame_layout.addWidget(summary_label)

                cell_text = chunk.get("cell_text", "")
                text_label = QLabel(cell_text)
                text_label.setWordWrap(True)
                text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                apply_label_style(text_label, "small")
                frame_layout.addWidget(text_label)

                parent_layout.addWidget(frame)
            except Exception as e:
                logger.error(f"Ошибка при добавлении совпадения в группу '{title}': {e}", exc_info=True)
                # Продолжаем обработку следующих совпадений
                continue

    def _handle_open_folder(self) -> None:
        if self.tender_folder and Path(self.tender_folder).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.tender_folder)))

