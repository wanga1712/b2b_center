"""
MODULE: scripts.fix_won_status
RESPONSIBILITY: Fixing records with 'Won' status that do not meet the criteria.
ALLOWED: psycopg2, psycopg2.extras, os, dotenv.
FORBIDDEN: None.
ERRORS: None.

Исправление записей со статусом 'Разыграна', которые не соответствуют условию
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("TENDER_MONITOR_DB_HOST"),
    database=os.getenv("TENDER_MONITOR_DB_DATABASE"),
    user=os.getenv("TENDER_MONITOR_DB_USER"),
    password=os.getenv("TENDER_MONITOR_DB_PASSWORD"),
    port=os.getenv("TENDER_MONITOR_DB_PORT", "5432")
)
cursor = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 70)
print("ИСПРАВЛЕНИЕ СТАТУСА 'РАЗЫГРАНА'")
print("=" * 70)

# Находим записи со статусом "Разыграна", которые не соответствуют условию
cursor.execute("""
    SELECT 
        id,
        status_id,
        end_date,
        delivery_end_date,
        (delivery_end_date - CURRENT_DATE)::integer as days_until_delivery
    FROM reestr_contract_44_fz
    WHERE status_id = 3
      AND (
          delivery_end_date IS NULL
          OR delivery_end_date < CURRENT_DATE + INTERVAL '90 days'
      )
    ORDER BY id
""")
wrong_records = cursor.fetchall()

print(f"\n📋 Найдено записей со статусом 'Разыграна', не соответствующих условию: {len(wrong_records)}")

if wrong_records:
    print("\n📋 Примеры проблемных записей:")
    for rec in wrong_records[:10]:
        days = rec['days_until_delivery'] if rec['days_until_delivery'] is not None else None
        print(f"  ID {rec['id']}: delivery_end_date={rec['delivery_end_date']}, "
              f"дней до поставки: {days}")
    
    # Исправляем статусы через SQL
    print("\n🔄 Исправление статусов...")
    
    # Сначала "Работа комиссии" (если подходит)
    cursor.execute("""
        UPDATE reestr_contract_44_fz
        SET status_id = 2
        WHERE status_id = 3
          AND (delivery_end_date IS NULL OR delivery_end_date < CURRENT_DATE + INTERVAL '90 days')
          AND end_date IS NOT NULL
          AND end_date > CURRENT_DATE
          AND end_date <= CURRENT_DATE + INTERVAL '90 days'
    """)
    commission_count = cursor.rowcount
    
    # Затем "Новая" (если подходит)
    cursor.execute("""
        UPDATE reestr_contract_44_fz
        SET status_id = 1
        WHERE status_id = 3
          AND (delivery_end_date IS NULL OR delivery_end_date < CURRENT_DATE + INTERVAL '90 days')
          AND end_date IS NOT NULL
          AND end_date <= CURRENT_DATE
    """)
    new_count = cursor.rowcount
    
    # Остальные -> "Плохие"
    cursor.execute("""
        UPDATE reestr_contract_44_fz
        SET status_id = 4
        WHERE status_id = 3
          AND (delivery_end_date IS NULL OR delivery_end_date < CURRENT_DATE + INTERVAL '90 days')
    """)
    bad_count = cursor.rowcount
    
    print(f"  Изменено на 'Работа комиссии': {commission_count}")
    print(f"  Изменено на 'Новая': {new_count}")
    print(f"  Изменено на 'Плохие': {bad_count}")
    
    conn.commit()
    print(f"\n✅ Исправлено записей: {len(wrong_records)}")
else:
    print("\n✅ Все записи со статусом 'Разыграна' соответствуют условию!")

cursor.close()
conn.close()

