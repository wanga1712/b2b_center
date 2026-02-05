"""
MODULE: services.archive_runner.processed_tenders_repository
RESPONSIBILITY: Repository for tracking processed tenders and files validity.
ALLOWED: TenderDatabaseManager, logging.
FORBIDDEN: Complex business logic (keep it CRUD-like).
ERRORS: None.

Репозиторий для отслеживания обработанных торгов и файлов.
"""

from typing import List, Dict, Any, Optional
from loguru import logger
from psycopg2.extras import RealDictCursor

from core.tender_database import TenderDatabaseManager


class ProcessedTendersRepository:
    """Репозиторий для работы с обработанными торгами и файлами."""

    def __init__(self, db_manager: TenderDatabaseManager):
        self.db_manager = db_manager

    def is_tender_processed(self, tender_id: int, registry_type: str, folder_name: str) -> bool:
        """
        Проверяет, была ли обработана торг.
        Использует данные из tender_document_matches.
        Проверяет только tender_id и registry_type, игнорируя folder_name
        (потому что folder_name может изменяться в зависимости от типа торга).

        Args:
            tender_id: ID торга
            registry_type: Тип реестра ('44fz', '223fz')
            folder_name: Имя папки торга (игнорируется в проверке)

        Returns:
            True если торг уже обработана
        """
        query = """
            SELECT id FROM tender_document_matches
            WHERE tender_id = %s AND registry_type = %s
        """

        try:
            result = self.db_manager.execute_query(query, (tender_id, registry_type))
            return len(result) > 0 if result else False
        except Exception as e:
            logger.warning(f"Ошибка проверки обработки торга {tender_id}: {e}")
            return False

    def mark_tender_processed(self, tender_id: int, registry_type: str, folder_name: str,
                             user_id: int, machine_id: Optional[str] = None,
                             error_message: Optional[str] = None) -> None:
        """
        Отмечает торг как обработанную.
        Использует tender_document_matches - просто логируем, данные уже там.

        Args:
            tender_id: ID торга
            registry_type: Тип реестра
            folder_name: Имя папки
            user_id: ID пользователя
            machine_id: ID машины (опционально)
            error_message: Сообщение об ошибке если обработка не удалась
        """
        status = 'failed' if error_message else 'completed'
        logger.debug(f"Торг {tender_id} ({registry_type}) отмечена как {status} (данные в tender_document_matches)")

        # Если есть ошибка, можно обновить error_reason в tender_document_matches
        if error_message:
            try:
                query = """
                    UPDATE tender_document_matches
                    SET error_reason = %s, folder_name = %s
                    WHERE tender_id = %s AND registry_type = %s
                """
                self.db_manager.execute_update(query, (f"processing_error: {error_message}", folder_name, tender_id, registry_type))
            except Exception as e:
                logger.warning(f"Ошибка обновления error_reason для торга {tender_id}: {e}")
        else:
            # Обновим folder_name для корректности
            try:
                query = """
                    UPDATE tender_document_matches
                    SET folder_name = %s
                    WHERE tender_id = %s AND registry_type = %s
                """
                self.db_manager.execute_update(query, (folder_name, tender_id, registry_type))
            except Exception as e:
                logger.debug(f"Не удалось обновить folder_name для торга {tender_id}: {e}")

    def mark_file_processed(self, tender_id: int, registry_type: str, file_path: str,
                           file_name: str, file_size: Optional[int], user_id: int,
                           machine_id: Optional[str] = None, error_message: Optional[str] = None) -> None:
        """
        Отмечает файл как обработанный.
        В текущей реализации файлы отслеживаются через tender_document_matches,
        поэтому этот метод просто логирует.
        """
        status = 'failed' if error_message else 'completed'
        logger.debug(f"Файл {file_name} отмечен как {status} (отслеживается через tender_document_matches)")

    def get_processing_stats(self, user_id: Optional[int] = None, days: int = 7) -> Dict[str, Any]:
        """
        Получает статистику обработки за последние дни из tender_document_matches.

        Args:
            user_id: ID пользователя (None для всех)
            days: Количество дней для статистики

        Returns:
            Словарь со статистикой
        """
        user_filter = "AND tdm.user_id = %s" if user_id else ""
        params = [days]
        if user_id:
            params.append(user_id)

        query = f"""
            SELECT
                COUNT(CASE WHEN tdm.is_interesting IS NOT NULL THEN 1 END) as completed_tenders,
                COUNT(CASE WHEN tdm.error_reason IS NOT NULL THEN 1 END) as failed_tenders,
                COUNT(*) as total_tenders,
                COUNT(DISTINCT tdm.folder_name) as unique_folders
            FROM tender_document_matches tdm
            WHERE tdm.processed_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            {user_filter}
        """

        try:
            result = self.db_manager.execute_query(query, tuple(params))
            if result:
                row = result[0]
                return {
                    'completed_tenders': row['completed_tenders'] or 0,
                    'failed_tenders': row['failed_tenders'] or 0,
                    'total_tenders': row['total_tenders'] or 0,
                    'unique_folders': row['unique_folders'] or 0,
                    'period_days': days
                }
        except Exception as e:
            logger.error(f"Ошибка получения статистики обработки: {e}")

        return {
            'completed_tenders': 0,
            'failed_tenders': 0,
            'total_tenders': 0,
            'unique_folders': 0,
            'period_days': days
        }

    def cleanup_old_records(self, days_to_keep: int = 90) -> int:
        """
        Очищает старые записи обработки.
        В текущей реализации использует tender_document_matches,
        поэтому очистка не производится (данные нужны для истории).

        Args:
            days_to_keep: Количество дней для хранения записей

        Returns:
            Всегда возвращает 0 (очистка не производится)
        """
        logger.info("Очистка старых записей отключена - используются данные из tender_document_matches")
        return 0
