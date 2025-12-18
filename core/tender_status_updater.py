"""
Модуль для автоматического обновления статусов закупок

Обеспечивает фоновое обновление статусов закупок при старте приложения
и периодическую проверку статусов существующих записей.
"""

from typing import Optional, Dict, Any
from loguru import logger
from PyQt5.QtCore import QThread, pyqtSignal
from psycopg2.extras import RealDictCursor

from core.tender_database import TenderDatabaseManager


STATUS_UPDATE_LOCK_ID = 1_000_001


class TenderStatusUpdater(QThread):
    """
    Поток для фонового обновления статусов закупок
    
    Запускается при старте приложения и обновляет:
    - Новые записи без статуса (status_id IS NULL)
    - Существующие записи с хорошими статусами (1, 2, 3)
    - Исключает "Плохие" (status_id = 4) из обновления
    """
    
    # Сигналы для уведомления о прогрессе
    status_updated = pyqtSignal(dict)  # Словарь с результатами обновления
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)  # Сообщение об ошибке
    
    def __init__(self, db_manager: TenderDatabaseManager, parent=None):
        """
        Инициализация обновлятеля статусов
        
        Args:
            db_manager: Менеджер подключения к БД tender_monitor
            parent: Родительский объект
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self._is_running = False
    
    def run(self):
        """Запуск обновления статусов в фоновом потоке"""
        self._is_running = True
        lock_acquired = False
        try:
            logger.info("Начало фонового обновления статусов закупок...")

            try:
                logger.debug(f"Попытка получить advisory lock с ID={STATUS_UPDATE_LOCK_ID}")
                lock_acquired = self.db_manager.acquire_advisory_lock(STATUS_UPDATE_LOCK_ID)
                logger.debug(f"Результат acquire_advisory_lock: {lock_acquired} (тип: {type(lock_acquired)})")
            except Exception as lock_error:
                logger.error(f"Ошибка при получении advisory lock: {lock_error}", exc_info=True)
                raise
            
            if not lock_acquired:
                logger.warning(
                    "Обновление статусов пропущено: блокировка уже удерживается другим процессом"
                )
                return

            logger.debug("Блокировка получена, начинаем обновление статусов...")
            results = self.update_all_statuses()
            logger.debug(f"Результат update_all_statuses: {results}")
            
            if results is not None:
                # Проверяем, были ли реально обновлены какие-то записи
                total_updated = sum(
                    sum(counts.values()) 
                    for counts in results.values()
                )
                if total_updated > 0:
                    logger.info(f"Статусы обновлены: {results}")
                    self.status_updated.emit(results)
                else:
                    logger.debug("Статусы проверены, но обновлений не требуется")
                    # Все равно отправляем результаты (даже если все 0)
                    self.status_updated.emit(results)
            else:
                logger.warning("Не удалось получить результаты обновления статусов")
                
        except Exception as e:
            # Детальная информация об ошибке
            error_type = type(e).__name__
            error_value = str(e) if e else repr(e)
            error_msg = f"Ошибка при обновлении статусов: {error_type}: {error_value}"
            logger.error(error_msg, exc_info=True)
            logger.error(f"Тип исключения: {type(e)}, Значение: {repr(e)}")
            self.error_occurred.emit(error_msg)
        finally:
            if lock_acquired:
                try:
                    released = self.db_manager.release_advisory_lock(STATUS_UPDATE_LOCK_ID)
                    if not released:
                        logger.warning(
                            "Advisory lock обновления статусов не был освобожден (не удерживался?)"
                        )
                except Exception as release_error:
                    logger.error(
                        "Не удалось освободить advisory lock обновления статусов: {}",
                        release_error,
                        exc_info=True
                    )
            self._is_running = False
            self.finished.emit()
            logger.info("Фоновое обновление статусов завершено")
    
    def update_all_statuses(self) -> Optional[Dict[str, Any]]:
        """
        Обновление статусов для всех закупок (44ФЗ и 223ФЗ)
        
        Returns:
            Словарь с результатами обновления или None в случае ошибки
        """
        try:
            # Вызываем функцию обновления статусов из БД
            query = "SELECT * FROM update_all_tender_statuses()"
            logger.debug(f"Выполнение запроса: {query}")
            results = self.db_manager.execute_query(query, None, RealDictCursor)
            logger.debug(f"Получено результатов: {len(results) if results else 0}")
            
            # Функция должна вернуть 2 строки (для 44ФЗ и 223ФЗ), даже если обновлено 0 записей
            if not results or len(results) == 0:
                logger.warning("Функция update_all_tender_statuses() не вернула результатов (возможно, функция не существует или выбрасывает исключение)")
                return None
            
            # Формируем словарь результатов
            stats = {}
            for row in results:
                table_name = row.get('table_name', 'unknown')
                stats[table_name] = {
                    'updated_new': row.get('updated_new', 0),
                    'updated_commission': row.get('updated_commission', 0),
                    'updated_won': row.get('updated_won', 0),
                    'updated_bad': row.get('updated_bad', 0)
                }
            
            # Логируем статистику (даже если все значения 0)
            for table_name, counts in stats.items():
                total = sum(counts.values())
                logger.debug(
                    f"{table_name}: "
                    f"Новая={counts['updated_new']}, "
                    f"Работа комиссии={counts['updated_commission']}, "
                    f"Разыграна={counts['updated_won']}, "
                    f"Плохие={counts['updated_bad']} "
                    f"(всего обновлено: {total})"
                )
                if total > 0:
                    logger.info(
                        f"{table_name}: "
                        f"Новая={counts['updated_new']}, "
                        f"Работа комиссии={counts['updated_commission']}, "
                        f"Разыграна={counts['updated_won']}, "
                        f"Плохие={counts['updated_bad']}"
                    )
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении статусов: {e}", exc_info=True)
            # Пробрасываем исключение дальше, чтобы оно было обработано в run()
            raise
    
    def stop(self):
        """Остановка обновления статусов"""
        self._is_running = False
    
    def is_running(self) -> bool:
        """Проверка, выполняется ли обновление"""
        return self._is_running


def ensure_status_update_functions(db_manager: TenderDatabaseManager) -> bool:
    """
    Проверка и создание функций обновления статусов в БД
    
    Args:
        db_manager: Менеджер подключения к БД
        
    Returns:
        True если функции созданы/существуют, False в случае ошибки
    """
    try:
        # Читаем SQL файл с функциями
        from pathlib import Path
        script_dir = Path(__file__).parent.parent
        sql_file = script_dir / 'scripts' / 'update_tender_statuses_function.sql'
        
        if not sql_file.exists():
            logger.warning(f"SQL файл с функциями не найден: {sql_file}")
            return False
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Выполняем SQL для создания функций
        db_manager.execute_query(sql_content, None)
        logger.info("Функции обновления статусов проверены/созданы")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при создании функций обновления статусов: {e}", exc_info=True)
        return False

