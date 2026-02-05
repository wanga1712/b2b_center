"""
MODULE: scripts.verify_and_recalculate_statuses
RESPONSIBILITY: Verifying current statuses and recalculating if necessary.
ALLOWED: psycopg2, psycopg2.extras, os, dotenv, sys, time, loguru.
FORBIDDEN: None.
ERRORS: None.

Проверка текущих статусов и пересчет при необходимости
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import sys
import time
from loguru import logger

load_dotenv()

logger.add("logs/verify_recalculate.log", rotation="10 MB", level="INFO")

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


def check_current_statuses(conn):
    """Проверка текущих статусов"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 70)
    print("ПРОВЕРКА ТЕКУЩИХ СТАТУСОВ")
    print("=" * 70)
    
    # Текущее распределение статусов
    cursor.execute("""
        SELECT 
            ts.name as status_name,
            COUNT(*)::bigint as count
        FROM reestr_contract_44_fz r
        LEFT JOIN tender_statuses ts ON r.status_id = ts.id
        GROUP BY ts.name, ts.id
        ORDER BY ts.id NULLS FIRST
    """)
    current_statuses = cursor.fetchall()
    
    print("\n📊 Текущее распределение статусов в reestr_contract_44_fz:")
    for stat in current_statuses:
        status_name = stat['status_name'] or "Без статуса"
        count = stat['count']
        print(f"  {status_name}: {count:,} записей")
    
    # Проверка неправильных статусов
    print("\n🔍 Проверка неправильных статусов:")
    
    # 1. Записи со статусом "Новая", но должны быть "Разыграна"
    cursor.execute("""
        SELECT COUNT(*)::bigint as count
        FROM reestr_contract_44_fz
        WHERE status_id = 1
          AND delivery_end_date IS NOT NULL
          AND delivery_end_date >= CURRENT_DATE + INTERVAL '90 days'
    """)
    wrong_new = cursor.fetchone()['count']
    print(f"  'Новая' → должна быть 'Разыграна': {wrong_new:,} записей")
    
    # 2. Записи со статусом "Работа комиссии", но должны быть "Разыграна"
    cursor.execute("""
        SELECT COUNT(*)::bigint as count
        FROM reestr_contract_44_fz
        WHERE status_id = 2
          AND delivery_end_date IS NOT NULL
          AND delivery_end_date >= CURRENT_DATE + INTERVAL '90 days'
    """)
    wrong_commission = cursor.fetchone()['count']
    print(f"  'Работа комиссии' → должна быть 'Разыграна': {wrong_commission:,} записей")
    
    # 3. Записи со статусом "Разыграна", но не должны быть
    cursor.execute("""
        SELECT COUNT(*)::bigint as count
        FROM reestr_contract_44_fz
        WHERE status_id = 3
          AND (delivery_end_date IS NULL OR delivery_end_date < CURRENT_DATE + INTERVAL '90 days')
    """)
    wrong_won = cursor.fetchone()['count']
    print(f"  'Разыграна' → неправильный статус: {wrong_won:,} записей")
    
    # 4. Записи со статусом "Новая", но должны быть "Работа комиссии"
    cursor.execute("""
        SELECT COUNT(*)::bigint as count
        FROM reestr_contract_44_fz
        WHERE status_id = 1
          AND end_date IS NOT NULL
          AND end_date > CURRENT_DATE
          AND end_date <= CURRENT_DATE + INTERVAL '90 days'
          AND (delivery_end_date IS NULL OR delivery_end_date < CURRENT_DATE + INTERVAL '90 days')
    """)
    wrong_new_commission = cursor.fetchone()['count']
    print(f"  'Новая' → должна быть 'Работа комиссии': {wrong_new_commission:,} записей")
    
    # 5. Записи со статусом "Работа комиссии", но должны быть "Новая"
    cursor.execute("""
        SELECT COUNT(*)::bigint as count
        FROM reestr_contract_44_fz
        WHERE status_id = 2
          AND end_date IS NOT NULL
          AND end_date <= CURRENT_DATE
          AND (delivery_end_date IS NULL OR delivery_end_date < CURRENT_DATE + INTERVAL '90 days')
    """)
    wrong_commission_new = cursor.fetchone()['count']
    print(f"  'Работа комиссии' → должна быть 'Новая': {wrong_commission_new:,} записей")
    
    total_wrong = wrong_new + wrong_commission + wrong_won + wrong_new_commission + wrong_commission_new
    
    print("\n" + "=" * 70)
    print(f"ИТОГО неправильных статусов: {total_wrong:,}")
    print("=" * 70)
    
    cursor.close()
    return total_wrong > 0


def recalculate_batch_44fz(cursor, status_id, condition, status_name):
    """Пересчет статусов для 44ФЗ батчами"""
    total_updated = 0
    batch_num = 0
    conn = cursor.connection
    
    print(f"\n🔄 Пересчет статуса '{status_name}' (status_id={status_id})...")
    logger.info(f"Начало пересчета статуса '{status_name}' для 44ФЗ")
    sys.stdout.flush()
    
    start_time = time.time()
    
    while True:
        batch_num += 1
        
        # Обновляем только записи, которые НЕ имеют нужный статус
        query = f"""
            WITH batch AS (
                SELECT id FROM reestr_contract_44_fz
                WHERE {condition}
                  AND (status_id IS NULL OR status_id != %s)
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
        cursor.execute(query, (status_id, status_id))
        updated_ids = cursor.fetchall()
        updated = len(updated_ids)
        
        if updated == 0:
            break
        
        conn.commit()
        
        total_updated += updated
        elapsed = time.time() - batch_start
        rate = updated / elapsed if elapsed > 0 else 0
        
        if updated_ids:
            last_id = min(row[0] for row in updated_ids)
        else:
            last_id = None
        
        print(
            f"  Батч #{batch_num}: обновлено {updated:,} записей "
            f"(всего: {total_updated:,}, скорость: {rate:,.0f} записей/сек, последний ID: {last_id})"
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
    logger.info(f"Завершен пересчет статуса '{status_name}': {total_updated:,} записей за {elapsed_total/60:.1f} минут")
    return total_updated


def recalculate_all_statuses(conn):
    """Пересчет всех статусов в правильном порядке"""
    cursor = conn.cursor()
    conn.set_session(autocommit=False)
    
    try:
        print("\n" + "=" * 70)
        print("ПЕРЕСЧЕТ СТАТУСОВ В ПРАВИЛЬНОМ ПОРЯДКЕ")
        print("=" * 70)
        print(f"Размер батча: {BATCH_SIZE:,} записей\n")
        sys.stdout.flush()
        
        total_updated = 0
        start_time_total = time.time()
        
        # 1. Разыграна (status_id = 3) - ПЕРВЫМ
        total_updated += recalculate_batch_44fz(
            cursor, 3,
            "delivery_end_date IS NOT NULL AND delivery_end_date >= CURRENT_DATE + INTERVAL '90 days'",
            "Разыграна"
        )
        
        # 2. Плохие (status_id = 4) - ВТОРЫМ
        total_updated += recalculate_batch_44fz(
            cursor, 4,
            "delivery_end_date IS NULL",
            "Плохие"
        )
        
        # 3. Работа комиссии (status_id = 2) - ТРЕТЬИМ
        total_updated += recalculate_batch_44fz(
            cursor, 2,
            """end_date IS NOT NULL 
               AND end_date > CURRENT_DATE 
               AND end_date <= CURRENT_DATE + INTERVAL '90 days'
               AND (delivery_end_date IS NULL OR delivery_end_date < CURRENT_DATE + INTERVAL '90 days')""",
            "Работа комиссии"
        )
        
        # 4. Новая (status_id = 1) - ПОСЛЕДНИМ
        total_updated += recalculate_batch_44fz(
            cursor, 1,
            """end_date IS NOT NULL 
               AND end_date <= CURRENT_DATE
               AND (delivery_end_date IS NULL OR delivery_end_date < CURRENT_DATE + INTERVAL '90 days')""",
            "Новая"
        )
        
        elapsed_total = time.time() - start_time_total
        print(f"\n✅ Всего обновлено: {total_updated:,} записей за {elapsed_total/60:.1f} минут")
        logger.info(f"Пересчет завершен: {total_updated:,} записей за {elapsed_total/60:.1f} минут")
        
        cursor.close()
        return total_updated
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ошибка при пересчете: {e}")
        logger.error(f"Ошибка при пересчете: {e}", exc_info=True)
        raise


def verify_final_statuses(conn):
    """Проверка финальных статусов после пересчета"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print("\n" + "=" * 70)
    print("ПРОВЕРКА ФИНАЛЬНЫХ СТАТУСОВ")
    print("=" * 70)
    
    # Финальное распределение
    cursor.execute("""
        SELECT 
            ts.name as status_name,
            COUNT(*)::bigint as count
        FROM reestr_contract_44_fz r
        LEFT JOIN tender_statuses ts ON r.status_id = ts.id
        GROUP BY ts.name, ts.id
        ORDER BY ts.id NULLS FIRST
    """)
    final_statuses = cursor.fetchall()
    
    print("\n📊 Финальное распределение статусов:")
    for stat in final_statuses:
        status_name = stat['status_name'] or "Без статуса"
        count = stat['count']
        print(f"  {status_name}: {count:,} записей")
    
    # Проверка, что все правильно
    cursor.execute("""
        SELECT COUNT(*)::bigint as count
        FROM reestr_contract_44_fz
        WHERE status_id = 1
          AND delivery_end_date IS NOT NULL
          AND delivery_end_date >= CURRENT_DATE + INTERVAL '90 days'
    """)
    still_wrong = cursor.fetchone()['count']
    
    if still_wrong == 0:
        print("\n✅ Все статусы установлены правильно!")
    else:
        print(f"\n⚠️  Осталось неправильных статусов: {still_wrong:,}")
    
    cursor.close()


def main():
    """Главная функция"""
    print("=" * 70)
    print("ПРОВЕРКА И ПЕРЕСЧЕТ СТАТУСОВ")
    print("=" * 70)
    
    logger.info("Начало проверки и пересчета статусов")
    
    conn = None
    try:
        conn = get_connection()
        
        # 1. Проверяем текущие статусы
        needs_recalculation = check_current_statuses(conn)
        
        if not needs_recalculation:
            print("\n✅ Все статусы установлены правильно, пересчет не требуется")
            return
        
        # 2. Пересчитываем статусы
        print("\n" + "=" * 70)
        response = input("Найдены неправильные статусы. Пересчитать? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Отменено")
            return
        
        total_updated = recalculate_all_statuses(conn)
        
        # 3. Проверяем финальные статусы
        verify_final_statuses(conn)
        
        print("\n" + "=" * 70)
        print("✅ ПРОВЕРКА И ПЕРЕСЧЕТ ЗАВЕРШЕНЫ")
        print("=" * 70)
        
        logger.info("Проверка и пересчет статусов завершены успешно")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем (Ctrl+C)")
        if conn:
            conn.rollback()
        logger.warning("Проверка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        error_msg = f"Ошибка: {e}"
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

