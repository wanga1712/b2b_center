"""
MODULE: scripts.apply_tender_statuses_migration_batched
RESPONSIBILITY: Applying tender statuses migration in batches to prevent locking.
ALLOWED: psycopg2, psycopg2.extras, os, dotenv, pathlib, loguru, time.
FORBIDDEN: None.
ERRORS: None.

Скрипт для применения миграции статусов закупок с батчами

Выполняет SQL миграцию по частям (батчами) для отслеживания прогресса
и предотвращения зависания при обновлении больших таблиц.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from pathlib import Path
from loguru import logger
import time

# Настройка логирования
logger.add("logs/migration.log", rotation="10 MB", level="INFO")

# Загружаем переменные окружения
load_dotenv()

# Размер батча для обновления
BATCH_SIZE = 50000  # Обновляем по 50k записей за раз


def get_tender_db_connection():
    """Получение подключения к базе данных tender_monitor"""
    host = os.getenv("TENDER_MONITOR_DB_HOST")
    database = os.getenv("TENDER_MONITOR_DB_DATABASE")
    user = os.getenv("TENDER_MONITOR_DB_USER")
    password = os.getenv("TENDER_MONITOR_DB_PASSWORD")
    port = os.getenv("TENDER_MONITOR_DB_PORT", "5432")
    
    if not all([host, database, user, password]):
        raise ValueError(
            "Не все параметры подключения к БД tender_monitor заданы в .env файле. "
            "Требуются: TENDER_MONITOR_DB_HOST, TENDER_MONITOR_DB_DATABASE, "
            "TENDER_MONITOR_DB_USER, TENDER_MONITOR_DB_PASSWORD"
        )
    
    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )
        logger.info(f"Успешное подключение к БД {database}")
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise


def update_status_batched(cursor, table_name: str, status_id: int, condition: str, status_name: str):
    """
    Обновление статусов батчами с логированием прогресса
    
    Args:
        cursor: Курсор БД
        table_name: Имя таблицы
        status_id: ID статуса для присвоения
        condition: SQL условие для WHERE (без WHERE)
        status_name: Название статуса для логирования
    """
    total_updated = 0
    batch_num = 0
    
    logger.info(f"\n🔄 Обновление статуса '{status_name}' (status_id={status_id}) для {table_name}...")
    
    while True:
        batch_num += 1
        start_time = time.time()
        
        # Обновляем батч
        query = f"""
            WITH batch AS (
                SELECT id FROM {table_name}
                WHERE {condition}
                LIMIT {BATCH_SIZE}
            )
            UPDATE {table_name} r
            SET status_id = %s
            FROM batch b
            WHERE r.id = b.id
        """
        
        cursor.execute(query, (status_id,))
        updated = cursor.rowcount
        
        if updated == 0:
            break
        
        total_updated += updated
        elapsed = time.time() - start_time
        
        logger.info(
            f"  Батч #{batch_num}: обновлено {updated:,} записей "
            f"(всего: {total_updated:,}, время: {elapsed:.2f} сек)"
        )
        
        # Коммитим после каждого батча
        cursor.connection.commit()
        
        # Небольшая пауза для снижения нагрузки
        if batch_num % 10 == 0:
            time.sleep(0.1)
    
    logger.info(f"✅ Статус '{status_name}' присвоен {total_updated:,} записям")
    return total_updated


def apply_migration_batched(conn):
    """Применение миграции батчами"""
    try:
        cursor = conn.cursor()
        conn.autocommit = False
        
        logger.info("=" * 60)
        logger.info("ШАГ 1: Создание таблицы статусов")
        logger.info("=" * 60)
        
        # Создаем таблицу статусов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tender_statuses (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Вставляем статусы
        cursor.execute("""
            INSERT INTO tender_statuses (id, name, description) VALUES
                (1, 'Новая', 'Закупка с end_date NOT NULL и end_date <= CURRENT_DATE (завершилась до текущей даты)'),
                (2, 'Работа комиссии', 'Закупка с end_date > CURRENT_DATE и end_date <= CURRENT_DATE + 90 дней (завершится в ближайшие 90 дней)'),
                (3, 'Разыграна', 'Закупка с delivery_end_date NOT NULL и delivery_end_date >= CURRENT_DATE + 90 дней (конец поставки не ранее чем через 90 дней)'),
                (4, 'Плохие', 'Закупка с delivery_end_date IS NULL (44ФЗ) или end_date > CURRENT_DATE + 180 дней (223ФЗ)')
            ON CONFLICT (id) DO NOTHING;
        """)
        
        cursor.execute("SELECT setval('tender_statuses_id_seq', (SELECT MAX(id) FROM tender_statuses), true);")
        conn.commit()
        logger.info("✅ Таблица статусов создана")
        
        logger.info("\n" + "=" * 60)
        logger.info("ШАГ 2: Добавление столбца status_id")
        logger.info("=" * 60)
        
        # Добавляем столбцы
        cursor.execute("ALTER TABLE reestr_contract_44_fz ADD COLUMN IF NOT EXISTS status_id INTEGER;")
        cursor.execute("ALTER TABLE reestr_contract_223_fz ADD COLUMN IF NOT EXISTS status_id INTEGER;")
        
        # Добавляем внешние ключи
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'fk_reestr_contract_44_fz_status_id'
                ) THEN
                    ALTER TABLE reestr_contract_44_fz
                    ADD CONSTRAINT fk_reestr_contract_44_fz_status_id
                    FOREIGN KEY (status_id) REFERENCES tender_statuses(id);
                END IF;
            END $$;
        """)
        
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'fk_reestr_contract_223_fz_status_id'
                ) THEN
                    ALTER TABLE reestr_contract_223_fz
                    ADD CONSTRAINT fk_reestr_contract_223_fz_status_id
                    FOREIGN KEY (status_id) REFERENCES tender_statuses(id);
                END IF;
            END $$;
        """)
        
        conn.commit()
        logger.info("✅ Столбцы status_id добавлены")
        
        logger.info("\n" + "=" * 60)
        logger.info("ШАГ 3: Присвоение статусов для reestr_contract_44_fz")
        logger.info("=" * 60)
        logger.info(f"Размер батча: {BATCH_SIZE:,} записей")
        logger.info("Это может занять несколько минут для больших таблиц...\n")
        
        total_44fz = 0
        
        # Новая (status_id = 1)
        total_44fz += update_status_batched(
            cursor, "reestr_contract_44_fz", 1,
            "end_date IS NOT NULL AND end_date <= CURRENT_DATE AND status_id IS NULL",
            "Новая"
        )
        
        # Работа комиссии (status_id = 2)
        total_44fz += update_status_batched(
            cursor, "reestr_contract_44_fz", 2,
            "end_date IS NOT NULL AND end_date > CURRENT_DATE AND end_date <= CURRENT_DATE + INTERVAL '90 days' AND status_id IS NULL",
            "Работа комиссии"
        )
        
        # Разыграна (status_id = 3)
        total_44fz += update_status_batched(
            cursor, "reestr_contract_44_fz", 3,
            "delivery_end_date IS NOT NULL AND delivery_end_date >= CURRENT_DATE + INTERVAL '90 days' AND status_id IS NULL",
            "Разыграна"
        )
        
        # Плохие (status_id = 4)
        total_44fz += update_status_batched(
            cursor, "reestr_contract_44_fz", 4,
            "delivery_end_date IS NULL AND status_id IS NULL",
            "Плохие"
        )
        
        logger.info(f"\n✅ Всего обновлено в reestr_contract_44_fz: {total_44fz:,} записей")
        
        logger.info("\n" + "=" * 60)
        logger.info("ШАГ 4: Присвоение статусов для reestr_contract_223_fz")
        logger.info("=" * 60)
        
        # Плохие для 223ФЗ
        total_223fz = update_status_batched(
            cursor, "reestr_contract_223_fz", 4,
            "end_date IS NOT NULL AND end_date > CURRENT_DATE + INTERVAL '180 days' AND status_id IS NULL",
            "Плохие"
        )
        
        logger.info(f"\n✅ Всего обновлено в reestr_contract_223_fz: {total_223fz:,} записей")
        
        logger.info("\n" + "=" * 60)
        logger.info("ШАГ 5: Создание индексов")
        logger.info("=" * 60)
        
        # Создаем индексы
        indexes = [
            ("idx_reestr_contract_44_fz_status_id", 
             "CREATE INDEX IF NOT EXISTS idx_reestr_contract_44_fz_status_id ON reestr_contract_44_fz(status_id) WHERE status_id IS NOT NULL"),
            ("idx_reestr_contract_223_fz_status_id",
             "CREATE INDEX IF NOT EXISTS idx_reestr_contract_223_fz_status_id ON reestr_contract_223_fz(status_id) WHERE status_id IS NOT NULL"),
            ("idx_reestr_contract_44_fz_status_end_date",
             "CREATE INDEX IF NOT EXISTS idx_reestr_contract_44_fz_status_end_date ON reestr_contract_44_fz(status_id, end_date) WHERE status_id IN (1, 2)"),
            ("idx_reestr_contract_44_fz_status_delivery_end_date",
             "CREATE INDEX IF NOT EXISTS idx_reestr_contract_44_fz_status_delivery_end_date ON reestr_contract_44_fz(status_id, delivery_end_date) WHERE status_id = 3"),
            ("idx_reestr_contract_223_fz_status_end_date",
             "CREATE INDEX IF NOT EXISTS idx_reestr_contract_223_fz_status_end_date ON reestr_contract_223_fz(status_id, end_date) WHERE status_id IS NULL OR status_id != 4"),
        ]
        
        for idx_name, idx_sql in indexes:
            logger.info(f"Создание индекса {idx_name}...")
            cursor.execute(idx_sql)
            conn.commit()
            logger.info(f"✅ Индекс {idx_name} создан")
        
        # Статистика
        logger.info("\n" + "=" * 60)
        logger.info("ШАГ 6: Статистика по статусам")
        logger.info("=" * 60)
        
        cursor.execute("""
            SELECT 
                ts.name as status_name,
                COUNT(*) as count
            FROM reestr_contract_44_fz r
            LEFT JOIN tender_statuses ts ON r.status_id = ts.id
            GROUP BY ts.name, ts.id
            ORDER BY ts.id
        """)
        
        logger.info("\n=== Статистика по статусам (reestr_contract_44_fz) ===")
        for row in cursor.fetchall():
            status_name = row[0] or "Без статуса"
            count = row[1]
            logger.info(f"  {status_name}: {count:,} записей")
        
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN r.status_id IS NULL THEN 'Без статуса (используются в поиске)'
                    ELSE ts.name 
                END as status_name,
                COUNT(*) as count
            FROM reestr_contract_223_fz r
            LEFT JOIN tender_statuses ts ON r.status_id = ts.id
            GROUP BY r.status_id, ts.name
            ORDER BY r.status_id NULLS FIRST
        """)
        
        logger.info("\n=== Статистика по статусам (reestr_contract_223_fz) ===")
        for row in cursor.fetchall():
            status_name = row[0]
            count = row[1]
            logger.info(f"  {status_name}: {count:,} записей")
        
        conn.commit()
        logger.info("\n✅ Миграция успешно применена!")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Ошибка при применении миграции: {e}", exc_info=True)
        raise
    finally:
        cursor.close()


def main():
    """Главная функция"""
    logger.info("=" * 60)
    logger.info("Применение миграции: Добавление статусов закупок (БАТЧАМИ)")
    logger.info("=" * 60)
    logger.info(f"Размер батча: {BATCH_SIZE:,} записей")
    logger.info("Это может занять 10-30 минут для таблиц с 22 млн записей")
    logger.info("Прогресс будет отображаться в реальном времени\n")
    
    try:
        # Подключаемся к БД
        conn = get_tender_db_connection()
        
        # Применяем миграцию батчами
        start_time = time.time()
        apply_migration_batched(conn)
        elapsed = time.time() - start_time
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ Миграция завершена успешно за {elapsed/60:.1f} минут!")
        logger.info("=" * 60)
        logger.info("\nСледующие шаги:")
        logger.info("1. Запросы в сервисах уже обновлены для использования статусов")
        logger.info("2. Записи с status_id = 4 (Плохие) автоматически исключаются из поиска")
        logger.info("3. Для 44ФЗ используются статусы 1, 2, 3")
        logger.info("4. Для 223ФЗ используются только записи без статуса (status_id IS NULL)")
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        raise
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("Соединение с БД закрыто")


if __name__ == "__main__":
    main()

