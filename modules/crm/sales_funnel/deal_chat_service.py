"""
MODULE: modules.crm.sales_funnel.deal_chat_service
RESPONSIBILITY: Service for managing deal chat messages.
ALLOWED: typing, traceback, loguru, psycopg2, core.tender_database.
FORBIDDEN: UI interaction.
ERRORS: None.

Сервис для работы с чатом по сделкам (deal_chat).
"""

from typing import List, Dict, Any, Optional
import traceback
from loguru import logger
from psycopg2.extras import RealDictCursor
from core.tender_database import TenderDatabaseManager


class DealChatService:
    """Сервис для работы с чатом сделки."""

    def __init__(self, db_manager: TenderDatabaseManager):
        self.db_manager = db_manager
        self._last_error = None
        # Проверяем и создаем таблицу, если её нет
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Проверка существования таблицы deal_chat и создание, если её нет."""
        try:
            # Убеждаемся, что подключение установлено
            if not self.db_manager._connection or self.db_manager._connection.closed:
                self.db_manager.connect()
            
            # Проверяем, существует ли таблица
            result = self.db_manager.execute_query(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'deal_chat'
                );
                """,
                (),
            )
            
            table_exists = result[0]['exists'] if result else False
            
            if not table_exists:
                logger.info("Таблица deal_chat не существует. Создаём...")
                self._create_table()
            else:
                logger.debug("Таблица deal_chat существует")
        except Exception as exc:
            logger.warning(f"Не удалось проверить существование таблицы deal_chat: {exc}. Попробуем создать...")
            try:
                self._create_table()
            except Exception as create_exc:
                logger.error(f"Не удалось создать таблицу deal_chat: {create_exc}", exc_info=True)

    def _create_table(self):
        """Создание таблицы deal_chat и индексов."""
        # Создание таблицы
        try:
            self.db_manager.execute_query(
                """
                CREATE TABLE IF NOT EXISTS deal_chat (
                    id BIGSERIAL PRIMARY KEY,
                    deal_id BIGINT NOT NULL REFERENCES sales_deals(id) ON DELETE CASCADE,
                    sender_id BIGINT,
                    sender_type TEXT NOT NULL CHECK (sender_type IN ('user', 'ai_agent')),
                    message_text TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    is_read BOOLEAN DEFAULT FALSE,
                    metadata JSONB
                );
                """,
                (),
            )
        except Exception as e:
            # Если таблица уже существует, это нормально
            if "already exists" not in str(e).lower():
                raise
            logger.debug("Таблица deal_chat уже существует")
        
        # Создание индексов
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_deal_chat_deal_id ON deal_chat(deal_id);",
            "CREATE INDEX IF NOT EXISTS idx_deal_chat_created_at ON deal_chat(created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_deal_chat_sender_id ON deal_chat(sender_id) WHERE sender_id IS NOT NULL;",
        ]
        
        for index_sql in indexes:
            try:
                self.db_manager.execute_query(index_sql, ())
            except Exception as e:
                # Игнорируем ошибки "уже существует"
                if "already exists" not in str(e).lower():
                    logger.warning(f"Предупреждение при создании индекса: {e}")
        
        logger.info("✅ Таблица deal_chat успешно создана!")

    def get_messages(self, deal_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получение сообщений чата по сделке.

        Args:
            deal_id: ID сделки
            limit: Максимальное количество сообщений (по умолчанию 100)

        Returns:
            Список сообщений, отсортированных по дате создания (старые первыми)
        """
        try:
            rows = self.db_manager.execute_query(
                """
                SELECT
                    id,
                    deal_id,
                    sender_id,
                    sender_type,
                    message_text,
                    created_at,
                    is_read,
                    metadata
                FROM deal_chat
                WHERE deal_id = %s
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (deal_id, limit),
                RealDictCursor,
            )
            return [dict(row) for row in rows] if rows else []
        except Exception as exc:
            # Если таблица не существует, возвращаем пустой список (таблица будет создана позже)
            error_msg = str(exc).lower()
            if "does not exist" in error_msg or "relation" in error_msg:
                logger.warning(f"Таблица deal_chat не существует для сделки {deal_id}. Чат будет недоступен до применения миграции.")
                return []
            logger.error(f"Ошибка при загрузке сообщений чата для сделки {deal_id}: {exc}", exc_info=True)
            return []

    def send_message(
        self,
        deal_id: int,
        sender_id: Optional[int],
        sender_type: str,
        message_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Отправка сообщения в чат сделки.

        Args:
            deal_id: ID сделки
            sender_id: ID пользователя-отправителя (None для AI-агента)
            sender_type: 'user' или 'ai_agent'
            message_text: Текст сообщения
            metadata: Дополнительные данные (опционально)

        Returns:
            ID созданного сообщения или None при ошибке
        """
        try:
            import json
            metadata_json = json.dumps(metadata) if metadata else None

            rows = self.db_manager.execute_query(
                """
                INSERT INTO deal_chat (deal_id, sender_id, sender_type, message_text, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                (deal_id, sender_id, sender_type, message_text, metadata_json),
                RealDictCursor,
            )
            if rows:
                message_id = rows[0]["id"]
                logger.info(f"Сообщение отправлено в чат сделки {deal_id}, message_id={message_id}")
                return message_id
            return None
        except Exception as exc:
            error_msg = str(exc)
            error_type = type(exc).__name__
            # Сохраняем детальную ошибку для показа пользователю
            self._last_error = {
                "error": error_msg,
                "error_type": error_type,
                "traceback": traceback.format_exc()
            }
            logger.error(f"Ошибка при отправке сообщения в чат сделки {deal_id}: {exc}", exc_info=True)
            return None

    def mark_as_read(self, deal_id: int, message_ids: List[int]) -> bool:
        """
        Отметить сообщения как прочитанные.

        Args:
            deal_id: ID сделки
            message_ids: Список ID сообщений

        Returns:
            True при успехе, False при ошибке
        """
        if not message_ids:
            return True

        try:
            placeholders = ",".join(["%s"] * len(message_ids))
            self.db_manager.execute_query(
                f"""
                UPDATE deal_chat
                SET is_read = TRUE
                WHERE deal_id = %s AND id IN ({placeholders})
                """,
                (deal_id, *message_ids),
            )
            return True
        except Exception as exc:
            logger.error(f"Ошибка при отметке сообщений как прочитанных: {exc}", exc_info=True)
            return False

    def get_users_list(self) -> List[Dict[str, Any]]:
        """
        Получение списка пользователей для выбора собеседника.

        Returns:
            Список пользователей из таблицы users
        """
        try:
            rows = self.db_manager.execute_query(
                """
                SELECT id, email, phone
                FROM users
                WHERE id IS NOT NULL
                ORDER BY id
                """,
                (),
                RealDictCursor,
            )
            return [dict(row) for row in rows] if rows else []
        except Exception as exc:
            logger.error(f"Ошибка при загрузке списка пользователей: {exc}", exc_info=True)
            return []

