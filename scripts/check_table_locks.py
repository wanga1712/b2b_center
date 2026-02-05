"""
MODULE: scripts.check_table_locks
RESPONSIBILITY: Checking locks on specific tender tables.
ALLOWED: sys, pathlib, psycopg2, config.settings, loguru, traceback.
FORBIDDEN: None.
ERRORS: None.

Проверка блокировок таблицы tender_document_matches.
"""

import sys
from pathlib import Path
import psycopg2

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import config
from loguru import logger


def main():
    """Основная функция."""
    logger.info("Проверка блокировок таблицы tender_document_matches...")
    
    db_config = config.tender_database
    
    try:
        conn = psycopg2.connect(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            user=db_config.user,
            password=db_config.password
        )
        
        with conn.cursor() as cursor:
            # Проверяем активные блокировки
            cursor.execute("""
                SELECT 
                    locktype, 
                    relation::regclass, 
                    mode, 
                    granted,
                    pid,
                    pg_blocking_pids(pid) as blocking_pids
                FROM pg_locks 
                WHERE relation = 'tender_document_matches'::regclass
                ORDER BY granted, pid
            """)
            
            locks = cursor.fetchall()
            
            if locks:
                logger.warning(f"⚠️  Найдено {len(locks)} блокировок на таблице tender_document_matches:")
                for lock in locks:
                    logger.warning(f"  - Тип: {lock[0]}, Режим: {lock[2]}, Предоставлена: {lock[3]}, PID: {lock[4]}, Блокируется: {lock[5]}")
            else:
                logger.info("✅ Активных блокировок на таблице нет")
            
            # Проверяем активные транзакции
            cursor.execute("""
                SELECT 
                    pid,
                    usename,
                    application_name,
                    state,
                    query_start,
                    state_change,
                    wait_event_type,
                    wait_event,
                    query
                FROM pg_stat_activity
                WHERE datname = current_database()
                AND state != 'idle'
                ORDER BY query_start
            """)
            
            transactions = cursor.fetchall()
            
            if transactions:
                logger.info(f"📊 Найдено {len(transactions)} активных транзакций:")
                for trans in transactions:
                    logger.info(f"  - PID: {trans[0]}, Пользователь: {trans[1]}, Приложение: {trans[2]}, Состояние: {trans[3]}")
                    if trans[6]:  # wait_event_type
                        logger.info(f"    Ожидает: {trans[6]} / {trans[7]}")
                    if trans[8] and len(trans[8]) < 200:  # query
                        logger.info(f"    Запрос: {trans[8][:200]}")
            else:
                logger.info("✅ Активных транзакций нет")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()

