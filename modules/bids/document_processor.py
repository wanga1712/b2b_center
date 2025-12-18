"""
Модуль для обработки документов тендеров.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from PyQt5.QtWidgets import QMessageBox

from modules.bids.process_output import ProcessOutputDialog


class DocumentProcessor:
    """Класс для обработки документов тендеров"""
    
    def __init__(self, user_id: int):
        """
        Инициализация процессора документов
        
        Args:
            user_id: ID пользователя
        """
        self.user_id = user_id
    
    def process_selected_tenders(
        self,
        selected_44fz: List[Dict[str, Any]],
        selected_223fz: List[Dict[str, Any]],
        parent_widget=None
    ):
        """Запуск обработки документов для выбранных закупок"""
        tender_ids_44fz = [t.get('id') for t in selected_44fz if t.get('id')]
        tender_ids_223fz = [t.get('id') for t in selected_223fz if t.get('id')]
        
        if not tender_ids_44fz and not tender_ids_223fz:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Ошибка", "Не удалось определить ID выбранных закупок")
            return
        
        tenders_arg = self._build_tenders_argument(tender_ids_44fz, tender_ids_223fz)
        cmd = self._build_command(tenders_arg)
        
        if not cmd:
            if parent_widget:
                script_path = self._get_script_path()
                QMessageBox.critical(
                    parent_widget,
                    "Ошибка",
                    f"Скрипт обработки документов не найден:\n{script_path}"
                )
            return
        
        total_count = len(tender_ids_44fz) + len(tender_ids_223fz)
        self._run_process(cmd, f"Анализ документации ({total_count} закупок)", parent_widget)
    
    def process_all_tenders(
        self,
        priority_44fz: List[Dict[str, Any]],
        priority_223fz: List[Dict[str, Any]],
        registry_type: Optional[str] = None,
        tender_type: str = 'new',
        parent_widget=None
    ):
        """
        Запуск обработки документов для всех закупок с учетом приоритетных
        
        Args:
            priority_44fz: Приоритетные закупки 44ФЗ
            priority_223fz: Приоритетные закупки 223ФЗ
            registry_type: Тип реестра для анализа ('44fz', '223fz' или None для обоих)
            tender_type: Тип торгов ('new' для новых, 'won' для разыгранных). По умолчанию 'new'.
            parent_widget: Родительский виджет для диалогов
        """
        priority_tender_ids = self._extract_priority_ids(priority_44fz, priority_223fz)
        
        if priority_tender_ids:
            ids_44fz = [t['id'] for t in priority_tender_ids if t.get('registry_type') == '44fz']
            ids_223fz = [t['id'] for t in priority_tender_ids if t.get('registry_type') == '223fz']
            tenders_arg = self._build_tenders_argument(ids_44fz, ids_223fz)
            cmd = self._build_command(tenders_arg, registry_type, tender_type, all_after_priority=True)
            dialog_title = f"Анализ всех закупок (приоритетных: {len(priority_tender_ids)})"
        else:
            cmd = self._build_command(None, registry_type, tender_type, all_after_priority=False)
            dialog_title = "Анализ всех закупок"
        
        if not cmd:
            if parent_widget:
                script_path = self._get_script_path()
                QMessageBox.critical(
                    parent_widget,
                    "Ошибка",
                    f"Скрипт обработки документов не найден:\n{script_path}"
                )
            return
        
        self._run_process(cmd, dialog_title, parent_widget, len(priority_tender_ids))
    
    def _get_script_path(self) -> Path:
        """Получение пути к скрипту обработки документов"""
        return Path(__file__).parent.parent.parent / "scripts" / "run_document_processing.py"
    
    def _build_tenders_argument(self, ids_44fz: List[int], ids_223fz: List[int]) -> str:
        """Построение аргумента --tenders из списков ID"""
        tenders_arg_parts = []
        if ids_44fz:
            ids_str = ','.join(map(str, ids_44fz))
            tenders_arg_parts.append(f"44fz:{ids_str}")
        if ids_223fz:
            ids_str = ','.join(map(str, ids_223fz))
            tenders_arg_parts.append(f"223fz:{ids_str}")
        return ' '.join(tenders_arg_parts)
    
    def _build_command(
        self,
        tenders_arg: Optional[str],
        registry_type: Optional[str] = None,
        tender_type: str = 'new',
        all_after_priority: bool = False
    ) -> Optional[List[str]]:
        """Построение команды для запуска скрипта"""
        script_path = self._get_script_path()
        if not script_path.exists():
            return None
        
        cmd = [sys.executable, str(script_path)]
        
        if tenders_arg:
            cmd.extend(['--tenders', tenders_arg])
        
        cmd.extend(['--user-id', str(self.user_id)])
        
        if all_after_priority:
            cmd.append('--all-after-priority')
        
        if registry_type:
            cmd.extend(['--registry-type', registry_type])
        
        cmd.extend(['--tender-type', tender_type])
        
        return cmd
    
    def _extract_priority_ids(
        self,
        priority_44fz: List[Dict[str, Any]],
        priority_223fz: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Извлечение приоритетных ID из списков закупок"""
        priority_tender_ids = []
        if priority_44fz:
            for t in priority_44fz:
                if t.get('id'):
                    priority_tender_ids.append({'id': t.get('id'), 'registry_type': '44fz'})
        if priority_223fz:
            for t in priority_223fz:
                if t.get('id'):
                    priority_tender_ids.append({'id': t.get('id'), 'registry_type': '223fz'})
        return priority_tender_ids
    
    def _run_process(
        self,
        cmd: List[str],
        dialog_title: str,
        parent_widget=None,
        priority_count: int = 0
    ) -> None:
        """Запуск процесса обработки документов"""
        try:
            process = self._create_process(cmd)
            
            if parent_widget:
                dialog = ProcessOutputDialog(parent_widget, dialog_title)
                dialog.start_process(process)
                dialog.show()
            
            if priority_count > 0:
                logger.info(f"Запущена обработка документов для всех закупок (приоритетных: {priority_count})")
            else:
                logger.info(f"Запущена обработка документов")
            logger.info(f"Команда: {' '.join(cmd)}")
        except Exception as error:
            logger.error(f"Ошибка при запуске обработки документов: {error}")
            logger.exception("Детали ошибки:")
            if parent_widget:
                QMessageBox.critical(parent_widget, "Ошибка", f"Не удалось запустить анализ документации:\n{error}")
    
    def _create_process(self, cmd: List[str]):
        """Создание процесса для запуска скрипта"""
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

