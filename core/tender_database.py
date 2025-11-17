"""
Менеджер базы данных tender_monitor

Отдельный модуль для работы с базой данных торгов.
Использует Singleton паттерн для единого подключения.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any, Tuple
from loguru import logger
from config.settings import DatabaseConfig
from core.exceptions import DatabaseConnectionError, DatabaseQueryError


class TenderDatabaseManager:
    """
    Менеджер базы данных tender_monitor (Singleton)
    
    Управляет подключением к базе данных торгов и выполнением запросов.
    """
    
    _instance: Optional['TenderDatabaseManager'] = None
    _connection: Optional[psycopg2.extensions.connection] = None
    
    def __new__(cls, config: Optional[DatabaseConfig] = None):
        """
        Реализация Singleton паттерна
        
        Args:
            config: Конфигурация базы данных (используется только при первом создании)
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = config
            cls._instance._connection = None
        return cls._instance
    
    def connect(self) -> None:
        """
        Установка подключения к базе данных
        
        Raises:
            DatabaseConnectionError: Если не удалось подключиться
        """
        if self._connection and not self._connection.closed:
            logger.debug("Подключение к БД tender_monitor уже установлено")
            return
        
        if not self._config:
            raise DatabaseConnectionError("Конфигурация БД tender_monitor не задана")
        
        try:
            self._connection = psycopg2.connect(
                host=self._config.host,
                database=self._config.database,
                user=self._config.user,
                password=self._config.password,
                port=self._config.port,
                cursor_factory=RealDictCursor
            )
            self._connection.autocommit = False
            logger.info(f"Успешное подключение к БД tender_monitor: {self._config.database}")
        except psycopg2.OperationalError as e:
            error_msg = f"Ошибка подключения к БД tender_monitor {self._config.database}: {e}"
            logger.error(error_msg)
            raise DatabaseConnectionError(error_msg) from e
        except Exception as e:
            error_msg = f"Неожиданная ошибка при подключении к БД tender_monitor: {e}"
            logger.error(error_msg)
            raise DatabaseConnectionError(error_msg) from e
    
    def disconnect(self) -> None:
        """Закрытие подключения к базе данных"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("Подключение к БД tender_monitor закрыто")
            self._connection = None
    
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        cursor_factory=None
    ) -> List[Dict[str, Any]]:
        """
        Выполнение SELECT запроса
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            cursor_factory: Фабрика курсора (например, RealDictCursor)
        
        Returns:
            Список результатов запроса в виде словарей
        
        Raises:
            DatabaseQueryError: Если произошла ошибка при выполнении запроса
        """
        if not self._connection or self._connection.closed:
            raise DatabaseConnectionError("Нет подключения к БД tender_monitor")
        
        try:
            # По умолчанию используем RealDictCursor для совместимости с DatabaseManager
            if cursor_factory is None:
                cursor_factory = RealDictCursor
            
            with self._connection.cursor(cursor_factory=cursor_factory) as cursor:
                cursor.execute(query, params)
                
                if query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall()
                    logger.debug(f"Выполнен SELECT запрос к tender_monitor, возвращено {len(result)} строк")
                    return result
                else:
                    self._connection.commit()
                    logger.debug(f"Выполнен запрос к tender_monitor: {query[:50]}...")
                    return []
        except psycopg2.Error as e:
            self._connection.rollback()
            error_msg = f"Ошибка выполнения запроса к БД tender_monitor: {e}"
            logger.error(error_msg)
            raise DatabaseQueryError(error_msg) from e
    
    def execute_update(
        self,
        query: str,
        params: Optional[Tuple] = None
    ) -> int:
        """
        Выполнение INSERT/UPDATE/DELETE запроса
        
        Args:
            query: SQL запрос
            params: Параметры запроса
        
        Returns:
            Количество затронутых строк
        
        Raises:
            DatabaseQueryError: Если произошла ошибка при выполнении запроса
        """
        if not self._connection or self._connection.closed:
            raise DatabaseConnectionError("Нет подключения к БД tender_monitor")
        
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(query, params)
                affected_rows = cursor.rowcount
                self._connection.commit()
                logger.debug(f"Выполнен UPDATE запрос, затронуто строк: {affected_rows}")
                return affected_rows
        except psycopg2.Error as e:
            self._connection.rollback()
            error_msg = f"Ошибка выполнения UPDATE запроса к БД tender_monitor: {e}"
            logger.error(error_msg)
            raise DatabaseQueryError(error_msg) from e
    
    def is_connected(self) -> bool:
        """Проверка наличия активного подключения"""
        return self._connection is not None and not self._connection.closed
    
    @classmethod
    def get_instance(cls) -> Optional['TenderDatabaseManager']:
        """Получение экземпляра Singleton"""
        return cls._instance

