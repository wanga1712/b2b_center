"""
MODULE: scripts.fix_commission_status
RESPONSIBILITY: Fixing records with 'Bad' status that should be 'Commission Work'.
ALLOWED: psycopg2, psycopg2.extras, os, dotenv, sys, time, traceback.
FORBIDDEN: None.
ERRORS: None.

Исправление записей со статусом 'Плохие', которые должны быть 'Работа комиссии'
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import sys
import time

load_dotenv()

BATCH_SIZE = 10000

conn = psycopg2.connect(
    host=os.getenv("TENDER_MONITOR_DB_HOST"),
    database=os.getenv("TENDER_MONITOR_DB_DATABASE"),
    user=os.getenv("TENDER_MONITOR_DB_USER"),
    password=os.getenv("TENDER_MONITOR_DB_PASSWORD"),
    port=os.getenv("TENDER_MONITOR_DB_PORT", "5432")
)
cursor = conn.cursor()
conn.set_session(autocommit=False)

try:
    print("=" * 70)
    print("ИСПРАВЛЕНИЕ СТАТУСА 'РАБОТА КОМИССИИ'")
    print("=" * 70)
    
    # Обновляем записи со статусом "Плохие", которые должны быть "Работа комиссии"
    print("\n🔄 Обновление записей со статусом 'Плохие' на 'Работа комиссии'...")
    
    total_updated = 0
    batch_num = 0
    
    while True:
        batch_num += 1
        
        query = """
            WITH batch AS (
                SELECT id FROM reestr_contract_44_fz
                WHERE status_id = 4
                  AND end_date IS NOT NULL
                  AND end_date > CURRENT_DATE
                  AND end_date <= CURRENT_DATE + INTERVAL '90 days'
                  AND (delivery_end_date IS NULL OR delivery_end_date < CURRENT_DATE + INTERVAL '90 days')
                ORDER BY id DESC
                LIMIT %s
            )
            UPDATE reestr_contract_44_fz r
            SET status_id = 2
            FROM batch b
            WHERE r.id = b.id
            RETURNING r.id
        """
        
        batch_start = time.time()
        cursor.execute(query, (BATCH_SIZE,))
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
        
        if batch_num % 5 == 0:
            time.sleep(0.05)
    
    print(f"\n✅ Обновлено записей: {total_updated:,}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    conn.rollback()
    print(f"\n❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    raise
finally:
    if conn:
        conn.close()

