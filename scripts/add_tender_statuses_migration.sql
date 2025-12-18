-- ============================================================================
-- Миграция: Добавление статусов закупок для оптимизации поиска
-- ============================================================================
-- 
-- Цель: Добавить систему статусов для закупок, чтобы исключать "плохие"
--       записи из поиска и ускорить запросы к БД
--
-- ⚠️ ВАЖНО: Данные НЕ удаляются! Скрипт только добавляет столбцы и обновляет
--           значения status_id. Все существующие данные остаются в БД.
--
-- Дата создания: 2025-12-05
-- ============================================================================

BEGIN;

-- ============================================================================
-- ШАГ 1: Создание таблицы статусов закупок
-- ============================================================================

CREATE TABLE IF NOT EXISTS tender_statuses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Вставка статусов
INSERT INTO tender_statuses (id, name, description) VALUES
    (1, 'Новая', 'Закупка с end_date NOT NULL и end_date <= CURRENT_DATE (завершилась до текущей даты)'),
    (2, 'Работа комиссии', 'Закупка с end_date > CURRENT_DATE и end_date <= CURRENT_DATE + 90 дней (завершится в ближайшие 90 дней)'),
    (3, 'Разыграна', 'Закупка с delivery_end_date NOT NULL и delivery_end_date >= CURRENT_DATE + 90 дней (конец поставки не ранее чем через 90 дней)'),
    (4, 'Плохие', 'Закупка с delivery_end_date IS NULL (44ФЗ) или end_date > CURRENT_DATE + 180 дней (223ФЗ)')
ON CONFLICT (id) DO NOTHING;

-- Устанавливаем последовательность для id на правильное значение
SELECT setval('tender_statuses_id_seq', (SELECT MAX(id) FROM tender_statuses), true);

-- ============================================================================
-- ШАГ 2: Добавление столбца status_id в reestr_contract_44_fz
-- ============================================================================

ALTER TABLE reestr_contract_44_fz 
ADD COLUMN IF NOT EXISTS status_id INTEGER;

-- Добавление внешнего ключа
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

-- ============================================================================
-- ШАГ 3: Добавление столбца status_id в reestr_contract_223_fz
-- ============================================================================

ALTER TABLE reestr_contract_223_fz 
ADD COLUMN IF NOT EXISTS status_id INTEGER;

-- Добавление внешнего ключа
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

-- ============================================================================
-- ШАГ 4: Присвоение статусов для reestr_contract_44_fz
-- ============================================================================

-- Новая: end_date NOT NULL AND end_date <= CURRENT_DATE
-- Все закупки, которые завершились до текущей даты
UPDATE reestr_contract_44_fz
SET status_id = 1
WHERE end_date IS NOT NULL 
  AND end_date <= CURRENT_DATE
  AND status_id IS NULL;

-- Работа комиссии: end_date > CURRENT_DATE AND end_date <= CURRENT_DATE + 90 дней
-- Закупки, которые еще не завершились, но завершатся в ближайшие 90 дней
-- После завершения (end_date <= CURRENT_DATE) они перейдут в статус "Новая"
UPDATE reestr_contract_44_fz
SET status_id = 2
WHERE end_date IS NOT NULL
  AND end_date > CURRENT_DATE
  AND end_date <= CURRENT_DATE + INTERVAL '90 days'
  AND status_id IS NULL;

-- Разыграна: delivery_end_date IS NOT NULL AND delivery_end_date >= CURRENT_DATE + 90 дней
-- Все закупки у которых определена delivery_end_date, она больше текущей даты,
-- и конец поставки не ранее, чем плюс 90 дней от текущей даты
UPDATE reestr_contract_44_fz
SET status_id = 3
WHERE delivery_end_date IS NOT NULL
  AND delivery_end_date >= CURRENT_DATE + INTERVAL '90 days'
  AND status_id IS NULL;

-- Плохие: delivery_end_date IS NULL
-- Закупки без даты окончания поставки
UPDATE reestr_contract_44_fz
SET status_id = 4
WHERE delivery_end_date IS NULL
  AND status_id IS NULL;

-- ============================================================================
-- ШАГ 5: Присвоение статусов для reestr_contract_223_fz
-- ============================================================================

DO $$
DECLARE
    v_updated INTEGER;
BEGIN
    -- Плохие: end_date позднее на 180 дней от текущей даты
    RAISE NOTICE 'Обновление статуса "Плохие" для reestr_contract_223_fz...';
    UPDATE reestr_contract_223_fz
    SET status_id = 4
    WHERE end_date IS NOT NULL
      AND end_date > CURRENT_DATE + INTERVAL '180 days'
      AND status_id IS NULL;
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RAISE NOTICE 'Обновлено записей со статусом "Плохие" в reestr_contract_223_fz: %', v_updated;
    RAISE NOTICE 'Остальные записи остаются без статуса (NULL) - они будут использоваться в поиске';
END $$;

-- ============================================================================
-- ШАГ 6: Создание индексов для ускорения поиска
-- ============================================================================

-- Индекс на status_id для reestr_contract_44_fz
CREATE INDEX IF NOT EXISTS idx_reestr_contract_44_fz_status_id 
ON reestr_contract_44_fz(status_id)
WHERE status_id IS NOT NULL;

-- Индекс на status_id для reestr_contract_223_fz
CREATE INDEX IF NOT EXISTS idx_reestr_contract_223_fz_status_id 
ON reestr_contract_223_fz(status_id)
WHERE status_id IS NOT NULL;

-- Композитный индекс для поиска новых закупок 44ФЗ (status_id + end_date)
CREATE INDEX IF NOT EXISTS idx_reestr_contract_44_fz_status_end_date 
ON reestr_contract_44_fz(status_id, end_date)
WHERE status_id IN (1, 2);

-- Композитный индекс для поиска разыгранных закупок 44ФЗ (status_id + delivery_end_date)
CREATE INDEX IF NOT EXISTS idx_reestr_contract_44_fz_status_delivery_end_date 
ON reestr_contract_44_fz(status_id, delivery_end_date)
WHERE status_id = 3;

-- Индекс для исключения плохих записей 223ФЗ
CREATE INDEX IF NOT EXISTS idx_reestr_contract_223_fz_status_end_date 
ON reestr_contract_223_fz(status_id, end_date)
WHERE status_id IS NULL OR status_id != 4;

-- ============================================================================
-- ШАГ 7: Создание функций для автоматического обновления статусов
-- ============================================================================

-- Функция для обновления статусов 44ФЗ
CREATE OR REPLACE FUNCTION update_tender_statuses_44fz()
RETURNS TABLE(
    updated_new INTEGER,
    updated_commission INTEGER,
    updated_won INTEGER,
    updated_bad INTEGER
) AS $$
DECLARE
    v_updated_new INTEGER := 0;
    v_updated_commission INTEGER := 0;
    v_updated_won INTEGER := 0;
    v_updated_bad INTEGER := 0;
BEGIN
    -- Обновление статуса "Новая"
    WITH updated AS (
        UPDATE reestr_contract_44_fz
        SET status_id = 1
        WHERE end_date IS NOT NULL 
          AND end_date <= CURRENT_DATE
          AND (status_id IS NULL OR status_id != 1)
          AND status_id != 4
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_new FROM updated;
    
    -- Обновление статуса "Работа комиссии"
    WITH updated AS (
        UPDATE reestr_contract_44_fz
        SET status_id = 2
        WHERE end_date IS NOT NULL
          AND end_date > CURRENT_DATE
          AND end_date <= CURRENT_DATE + INTERVAL '90 days'
          AND (status_id IS NULL OR status_id != 2)
          AND status_id != 4
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_commission FROM updated;
    
    -- Обновление статуса "Разыграна"
    WITH updated AS (
        UPDATE reestr_contract_44_fz
        SET status_id = 3
        WHERE delivery_end_date IS NOT NULL
          AND delivery_end_date >= CURRENT_DATE + INTERVAL '90 days'
          AND (status_id IS NULL OR status_id != 3)
          AND status_id != 4
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_won FROM updated;
    
    -- Обновление статуса "Плохие"
    WITH updated AS (
        UPDATE reestr_contract_44_fz
        SET status_id = 4
        WHERE delivery_end_date IS NULL
          AND status_id IS NULL
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_bad FROM updated;
    
    RETURN QUERY SELECT v_updated_new, v_updated_commission, v_updated_won, v_updated_bad;
END;
$$ LANGUAGE plpgsql;

-- Функция для обновления статусов 223ФЗ
CREATE OR REPLACE FUNCTION update_tender_statuses_223fz()
RETURNS TABLE(
    updated_bad INTEGER
) AS $$
DECLARE
    v_updated_bad INTEGER := 0;
BEGIN
    WITH updated AS (
        UPDATE reestr_contract_223_fz
        SET status_id = 4
        WHERE end_date IS NOT NULL
          AND end_date > CURRENT_DATE + INTERVAL '180 days'
          AND status_id IS NULL
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_bad FROM updated;
    
    RETURN QUERY SELECT v_updated_bad;
END;
$$ LANGUAGE plpgsql;

-- Функция для обновления всех статусов
CREATE OR REPLACE FUNCTION update_all_tender_statuses()
RETURNS TABLE(
    table_name TEXT,
    updated_new INTEGER,
    updated_commission INTEGER,
    updated_won INTEGER,
    updated_bad INTEGER
) AS $$
DECLARE
    v_44fz_new INTEGER;
    v_44fz_commission INTEGER;
    v_44fz_won INTEGER;
    v_44fz_bad INTEGER;
    v_223fz_bad INTEGER;
BEGIN
    SELECT * INTO v_44fz_new, v_44fz_commission, v_44fz_won, v_44fz_bad
    FROM update_tender_statuses_44fz();
    
    SELECT * INTO v_223fz_bad
    FROM update_tender_statuses_223fz();
    
    RETURN QUERY SELECT 
        'reestr_contract_44_fz'::TEXT,
        v_44fz_new,
        v_44fz_commission,
        v_44fz_won,
        v_44fz_bad;
    
    RETURN QUERY SELECT 
        'reestr_contract_223_fz'::TEXT,
        0, 0, 0,
        v_223fz_bad;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- ШАГ 8: Статистика по статусам
-- ============================================================================

-- Выводим статистику для проверки
SELECT 
    'reestr_contract_44_fz' as table_name,
    ts.name as status_name,
    COUNT(*) as count
FROM reestr_contract_44_fz r
LEFT JOIN tender_statuses ts ON r.status_id = ts.id
GROUP BY ts.name
ORDER BY ts.id;

SELECT 
    'reestr_contract_223_fz' as table_name,
    CASE 
        WHEN status_id IS NULL THEN 'Без статуса (используются в поиске)'
        ELSE ts.name 
    END as status_name,
    COUNT(*) as count
FROM reestr_contract_223_fz r
LEFT JOIN tender_statuses ts ON r.status_id = ts.id
GROUP BY status_id, ts.name
ORDER BY status_id NULLS FIRST;

COMMIT;

-- ============================================================================
-- ПРИМЕЧАНИЯ:
-- ============================================================================
-- 1. После выполнения миграции нужно обновить запросы в сервисах:
--    - Исключать записи с status_id = 4 (Плохие) из поиска
--    - Для 44ФЗ использовать статусы 1, 2, 3
--    - Для 223ФЗ использовать только записи без статуса (status_id IS NULL)
--
-- 2. Рекомендуется создать задачу cron для периодического обновления статусов
--    (например, раз в день), так как статусы зависят от CURRENT_DATE
--
-- 3. Индексы созданы с условиями WHERE для оптимизации размера индексов
--    и ускорения запросов
-- ============================================================================

