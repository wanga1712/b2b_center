"""
MODULE: scripts.apply_migration_with_batches
RESPONSIBILITY: Batched migration application including data updates.
ALLOWED: psycopg2, psycopg2.extras, os, dotenv, sys, time, loguru.
FORBIDDEN: None.
ERRORS: None.

Миграция статусов закупок: структура + обновление данных батчами
Начинает с последних записей, пропускает уже обработанные
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import sys
import time
from loguru import logger

load_dotenv()

# Настройка логирования
logger.add("logs/migration.log", rotation="10 MB", level="INFO")

# Размер батча
BATCH_SIZE = 10000


def get_connection():
    """Получение подключения к БД"""
    return psycopg2.connect(
        host=os.getenv("TENDER_MONITOR_DB_HOST"),
        database=os.getenv("TENDER_MONITOR_DB_DATABASE"),
        user=os.getenv("TENDER_MONITOR_DB_USER"),
        password=os.getenv("TENDER_MONITOR_DB_PASSWORD"),
        port=os.getenv("TENDER_MONITOR_DB_PORT", "5432"),
        connect_timeout=10
    )


def create_structure(conn):
    """Создание структуры: таблицы, столбцы, связи"""
    cursor = conn.cursor()
    conn.set_session(autocommit=True)
    
    try:
        print("\n" + "=" * 70)
        print("ШАГ 1: Создание таблицы статусов")
        print("=" * 70)
        sys.stdout.flush()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tender_statuses (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✅ Таблица tender_statuses создана")
        sys.stdout.flush()
        
        print("\nВставка статусов...")
        sys.stdout.flush()
        
        cursor.execute("""
            INSERT INTO tender_statuses (id, name, description) VALUES
                (1, 'Новая', 'Закупка с end_date NOT NULL и end_date <= CURRENT_DATE'),
                (2, 'Работа комиссии', 'Закупка с end_date > CURRENT_DATE и end_date <= CURRENT_DATE + 90 дней'),
                (3, 'Разыграна', 'Закупка с delivery_end_date NOT NULL и delivery_end_date >= CURRENT_DATE + 90 дней'),
                (4, 'Плохие', 'Закупка с delivery_end_date IS NULL (44ФЗ) или end_date > CURRENT_DATE + 180 дней (223ФЗ)')
            ON CONFLICT (id) DO NOTHING;
        """)
        cursor.execute("SELECT setval('tender_statuses_id_seq', (SELECT MAX(id) FROM tender_statuses), true);")
        print("✅ Статусы вставлены")
        sys.stdout.flush()
        
        print("\n" + "=" * 70)
        print("ШАГ 2: Добавление столбца status_id в reestr_contract_44_fz")
        print("=" * 70)
        sys.stdout.flush()
        
        cursor.execute("ALTER TABLE reestr_contract_44_fz ADD COLUMN IF NOT EXISTS status_id INTEGER;")
        print("✅ Столбец status_id добавлен")
        sys.stdout.flush()
        
        print("\nСоздание внешнего ключа...")
        sys.stdout.flush()
        
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
        print("✅ Внешний ключ создан")
        sys.stdout.flush()
        
        print("\n" + "=" * 70)
        print("ШАГ 3: Добавление столбца status_id в reestr_contract_223_fz")
        print("=" * 70)
        sys.stdout.flush()
        
        cursor.execute("ALTER TABLE reestr_contract_223_fz ADD COLUMN IF NOT EXISTS status_id INTEGER;")
        print("✅ Столбец status_id добавлен")
        sys.stdout.flush()
        
        print("\nСоздание внешнего ключа...")
        sys.stdout.flush()
        
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
        print("✅ Внешний ключ создан")
        sys.stdout.flush()
        
        cursor.close()
        logger.info("Структура БД создана успешно")
        
    except Exception as e:
        print(f"\n❌ Ошибка при создании структуры: {e}")
        logger.error(f"Ошибка при создании структуры: {e}", exc_info=True)
        raise


def update_batch_44fz(cursor, status_id, condition, status_name, start_from_id=None):
    """
    Обновление статусов для 44ФЗ батчами, начиная с последних записей
    
    Args:
        cursor: Курсор БД
        status_id: ID статуса
        condition: SQL условие (без WHERE и без проверки status_id)
        status_name: Название статуса
        start_from_id: Начальный ID (для продолжения с места остановки)
    """
    total_updated = 0
    batch_num = 0
    conn = cursor.connection
    
    print(f"\n🔄 Обновление статуса '{status_name}' (status_id={status_id}) для 44ФЗ...")
    logger.info(f"Начало обновления статуса '{status_name}' для 44ФЗ")
    sys.stdout.flush()
    
    start_time = time.time()
    
    while True:
        batch_num += 1
        
        # Формируем условие с проверкой на NULL status_id и начинаем с последних записей
        where_clause = f"{condition} AND status_id IS NULL"
        if start_from_id:
            where_clause += f" AND id < {start_from_id}"
        
        # Обновляем батч, начиная с последних записей
        query = f"""
            WITH batch AS (
                SELECT id FROM reestr_contract_44_fz
                WHERE {where_clause}
                ORDER BY id DESC
                LIMIT {BATCH_SIZE}
            )
            UPDATE reestr_contract_44_fz r
            SET status_id = %s
            FROM batch b
            WHERE r.id = b.id
            RETURNING r.id
        """
        
        batch_start = time.time()
        cursor.execute(query, (status_id,))
        updated_ids = cursor.fetchall()
        updated = len(updated_ids)
        
        if updated == 0:
            break
        
        # Коммитим сразу после каждого батча
        conn.commit()
        
        total_updated += updated
        elapsed = time.time() - batch_start
        elapsed_total = time.time() - start_time
        rate = updated / elapsed if elapsed > 0 else 0
        
        # Получаем минимальный ID из батча для следующей итерации
        if updated_ids:
            start_from_id = min(row[0] for row in updated_ids)
        
        print(
            f"  Батч #{batch_num}: обновлено {updated:,} записей "
            f"(всего: {total_updated:,}, время: {elapsed:.2f} сек, "
            f"скорость: {rate:,.0f} записей/сек, последний ID: {start_from_id})"
        )
        sys.stdout.flush()
        logger.info(
            f"Батч #{batch_num}: обновлено {updated:,} записей "
            f"(всего: {total_updated:,}, скорость: {rate:,.0f} записей/сек)"
        )
        
        # Небольшая пауза каждые 5 батчей
        if batch_num % 5 == 0:
            time.sleep(0.05)
    
    elapsed_total = time.time() - start_time
    print(f"✅ Статус '{status_name}' присвоен {total_updated:,} записям за {elapsed_total/60:.1f} минут")
    logger.info(f"Завершено обновление статуса '{status_name}': {total_updated:,} записей за {elapsed_total/60:.1f} минут")
    return total_updated


def update_batch_223fz(cursor, status_id, condition, status_name, start_from_id=None):
    """Обновление статусов для 223ФЗ батчами"""
    total_updated = 0
    batch_num = 0
    conn = cursor.connection
    
    print(f"\n🔄 Обновление статуса '{status_name}' (status_id={status_id}) для 223ФЗ...")
    logger.info(f"Начало обновления статуса '{status_name}' для 223ФЗ")
    sys.stdout.flush()
    
    start_time = time.time()
    
    while True:
        batch_num += 1
        
        where_clause = f"{condition} AND status_id IS NULL"
        if start_from_id:
            where_clause += f" AND id < {start_from_id}"
        
        query = f"""
            WITH batch AS (
                SELECT id FROM reestr_contract_223_fz
                WHERE {where_clause}
                ORDER BY id DESC
                LIMIT {BATCH_SIZE}
            )
            UPDATE reestr_contract_223_fz r
            SET status_id = %s
            FROM batch b
            WHERE r.id = b.id
            RETURNING r.id
        """
        
        batch_start = time.time()
        cursor.execute(query, (status_id,))
        updated_ids = cursor.fetchall()
        updated = len(updated_ids)
        
        if updated == 0:
            break
        
        conn.commit()
        
        total_updated += updated
        elapsed = time.time() - batch_start
        rate = updated / elapsed if elapsed > 0 else 0
        
        if updated_ids:
            start_from_id = min(row[0] for row in updated_ids)
        
        print(
            f"  Батч #{batch_num}: обновлено {updated:,} записей "
            f"(всего: {total_updated:,}, время: {elapsed:.2f} сек, "
            f"скорость: {rate:,.0f} записей/сек, последний ID: {start_from_id})"
        )
        sys.stdout.flush()
        logger.info(
            f"Батч #{batch_num}: обновлено {updated:,} записей "
            f"(всего: {total_updated:,}, скорость: {rate:,.0f} записей/сек)"
        )
        
        if batch_num % 5 == 0:
            time.sleep(0.05)
    
    elapsed_total = time.time() - start_time
    print(f"✅ Статус '{status_name}' присвоен {total_updated:,} записям за {elapsed_total/60:.1f} минут")
    logger.info(f"Завершено обновление статуса '{status_name}': {total_updated:,} записей за {elapsed_total/60:.1f} минут")
    return total_updated


def update_data(conn):
    """Обновление данных батчами"""
    cursor = conn.cursor()
    conn.set_session(autocommit=False)  # Ручной коммит для батчей
    
    try:
        print("\n" + "=" * 70)
        print("ШАГ 4: Обновление статусов для reestr_contract_44_fz (БАТЧАМИ)")
        print("=" * 70)
        print(f"Размер батча: {BATCH_SIZE:,} записей")
        print("Начинаем с последних записей (ORDER BY id DESC)")
        print("Пропускаем записи, где status_id уже установлен")
        print("Коммитим после каждого батча\n")
        sys.stdout.flush()
        
        total_44fz = 0
        start_time_total = time.time()
        
        # ВАЖНО: Порядок имеет значение! Сначала проверяем более специфичные условия
        
        # Разыграна (status_id = 3) - ПЕРВЫМ, т.к. это более специфичное условие
        # Закупка с delivery_end_date, которая еще не завершена (end_date > CURRENT_DATE)
        # или уже завершена, но поставка в будущем
        total_44fz += update_batch_44fz(
            cursor, 3,
            "delivery_end_date IS NOT NULL AND delivery_end_date >= CURRENT_DATE + INTERVAL '90 days'",
            "Разыграна"
        )
        
        # Плохие (status_id = 4) - ВТОРЫМ
        total_44fz += update_batch_44fz(
            cursor, 4,
            "delivery_end_date IS NULL",
            "Плохие"
        )
        
        # Работа комиссии (status_id = 2) - ТРЕТЬИМ
        # Только те, которые еще не получили статус "Разыграна"
        total_44fz += update_batch_44fz(
            cursor, 2,
            "end_date IS NOT NULL AND end_date > CURRENT_DATE AND end_date <= CURRENT_DATE + INTERVAL '90 days'",
            "Работа комиссии"
        )
        
        # Новая (status_id = 1) - ПОСЛЕДНИМ
        # Все остальные с end_date <= CURRENT_DATE
        total_44fz += update_batch_44fz(
            cursor, 1,
            "end_date IS NOT NULL AND end_date <= CURRENT_DATE",
            "Новая"
        )
        
        elapsed_44fz = time.time() - start_time_total
        print(f"\n✅ Всего обновлено в reestr_contract_44_fz: {total_44fz:,} записей за {elapsed_44fz/60:.1f} минут")
        logger.info(f"Обновление 44ФЗ завершено: {total_44fz:,} записей за {elapsed_44fz/60:.1f} минут")
        
        print("\n" + "=" * 70)
        print("ШАГ 5: Обновление статусов для reestr_contract_223_fz (БАТЧАМИ)")
        print("=" * 70)
        sys.stdout.flush()
        
        start_time_223fz = time.time()
        
        # Плохие для 223ФЗ
        total_223fz = update_batch_223fz(
            cursor, 4,
            "end_date IS NOT NULL AND end_date > CURRENT_DATE + INTERVAL '180 days'",
            "Плохие"
        )
        
        elapsed_223fz = time.time() - start_time_223fz
        print(f"\n✅ Всего обновлено в reestr_contract_223_fz: {total_223fz:,} записей за {elapsed_223fz/60:.1f} минут")
        logger.info(f"Обновление 223ФЗ завершено: {total_223fz:,} записей за {elapsed_223fz/60:.1f} минут")
        
        cursor.close()
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ошибка при обновлении данных: {e}")
        logger.error(f"Ошибка при обновлении данных: {e}", exc_info=True)
        raise


def create_indexes(conn):
    """Создание индексов"""
    # Закоммитим текущую транзакцию перед изменением режима
    conn.commit()
    conn.set_session(autocommit=True)
    
    cursor = conn.cursor()
    
    try:
        print("\n" + "=" * 70)
        print("ШАГ 6: Создание индексов")
        print("=" * 70)
        sys.stdout.flush()
        
        indexes = [
            ("idx_reestr_contract_44_fz_status_id",
             "CREATE INDEX IF NOT EXISTS idx_reestr_contract_44_fz_status_id ON reestr_contract_44_fz(status_id) WHERE status_id IS NOT NULL"),
            ("idx_reestr_contract_223_fz_status_id",
             "CREATE INDEX IF NOT EXISTS idx_reestr_contract_223_fz_status_id ON reestr_contract_223_fz(status_id) WHERE status_id IS NOT NULL"),
        ]
        
        for idx_name, idx_sql in indexes:
            print(f"\nСоздание индекса: {idx_name}...")
            sys.stdout.flush()
            start_idx = time.time()
            cursor.execute(idx_sql)
            elapsed_idx = time.time() - start_idx
            print(f"✅ Создан за {elapsed_idx:.2f} секунд")
            sys.stdout.flush()
            logger.info(f"Индекс {idx_name} создан за {elapsed_idx:.2f} секунд")
        
        cursor.close()
        
    except Exception as e:
        print(f"\n❌ Ошибка при создании индексов: {e}")
        logger.error(f"Ошибка при создании индексов: {e}", exc_info=True)
        raise


def main():
    """Главная функция"""
    print("=" * 70)
    print("МИГРАЦИЯ: Структура + Обновление данных батчами")
    print("=" * 70)
    print(f"Размер батча: {BATCH_SIZE:,} записей")
    print("Начинаем с последних записей (ORDER BY id DESC)")
    print("Пропускаем уже обработанные (status_id IS NOT NULL)")
    print("Коммитим после каждого батча\n")
    
    logger.info("=" * 70)
    logger.info("Начало миграции статусов закупок")
    logger.info("=" * 70)
    
    conn = None
    try:
        conn = get_connection()
        
        # 1. Создаем структуру
        create_structure(conn)
        
        # 2. Обновляем данные батчами
        update_data(conn)
        
        # 3. Создаем индексы
        create_indexes(conn)
        
        print("\n" + "=" * 70)
        print("✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 70)
        print("\nСледующие шаги:")
        print("1. Запросы в сервисах уже обновлены для использования статусов")
        print("2. Записи с status_id = 4 (Плохие) автоматически исключаются из поиска")
        print("3. При следующем запуске приложения статусы будут обновляться автоматически в фоне")
        
        logger.info("Миграция завершена успешно")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем (Ctrl+C)")
        if conn:
            conn.rollback()
        logger.warning("Миграция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        error_msg = f"Критическая ошибка: {e}"
        print(f"\n❌ {error_msg}")
        logger.error(error_msg, exc_info=True)
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
            print("\nСоединение с БД закрыто")
            logger.info("Соединение с БД закрыто")


if __name__ == "__main__":
    main()

