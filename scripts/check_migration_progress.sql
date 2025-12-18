-- Скрипт для проверки прогресса миграции статусов
-- Запустите в отдельном окне psql или другом терминале

-- Проверка текущих активных запросов
SELECT 
    pid,
    usename,
    application_name,
    state,
    query_start,
    now() - query_start as duration,
    LEFT(query, 100) as query_preview
FROM pg_stat_activity
WHERE state != 'idle'
  AND query NOT LIKE '%pg_stat_activity%'
ORDER BY query_start;

-- Проверка прогресса обновления статусов
SELECT 
    'reestr_contract_44_fz' as table_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN status_id IS NOT NULL THEN 1 END) as with_status,
    COUNT(CASE WHEN status_id IS NULL THEN 1 END) as without_status,
    COUNT(CASE WHEN status_id = 1 THEN 1 END) as status_new,
    COUNT(CASE WHEN status_id = 2 THEN 1 END) as status_commission,
    COUNT(CASE WHEN status_id = 3 THEN 1 END) as status_won,
    COUNT(CASE WHEN status_id = 4 THEN 1 END) as status_bad
FROM reestr_contract_44_fz;

SELECT 
    'reestr_contract_223_fz' as table_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN status_id IS NOT NULL THEN 1 END) as with_status,
    COUNT(CASE WHEN status_id IS NULL THEN 1 END) as without_status,
    COUNT(CASE WHEN status_id = 4 THEN 1 END) as status_bad
FROM reestr_contract_223_fz;

-- Проверка блокировок (если миграция блокирует таблицу)
SELECT 
    locktype,
    relation::regclass,
    mode,
    granted,
    pid
FROM pg_locks
WHERE relation::regclass::text IN ('reestr_contract_44_fz', 'reestr_contract_223_fz')
ORDER BY relation;

