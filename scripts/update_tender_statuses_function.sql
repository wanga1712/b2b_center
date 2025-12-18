-- ============================================================================
-- Функция для автоматического обновления статусов закупок
-- ============================================================================
-- 
-- Правила присвоения статусов:
-- 1. НОВЫЕ (status_id = 1): end_date >= CURRENT_DATE
-- 2. РАБОТА КОМИССИИ (status_id = 2): end_date < CURRENT_DATE 
--    И end_date >= CURRENT_DATE - 90 дней 
--    И delivery_end_date IS NULL
-- 3. РАЗЫГРАННЫЕ (status_id = 3): delivery_end_date IS NOT NULL 
--    И delivery_end_date >= CURRENT_DATE + 90 дней
-- 4. ПЛОХИЕ (status_id = 4): все остальные, которые не подходят под условия выше
--
-- ВАЖНО: Все статусы перезаписываются, включая "Плохие" (status_id = 4)
-- ============================================================================

-- Удаляем старые функции, если они существуют (для изменения типа возвращаемого значения)
DROP FUNCTION IF EXISTS update_tender_statuses_44fz() CASCADE;
DROP FUNCTION IF EXISTS update_tender_statuses_223fz() CASCADE;
DROP FUNCTION IF EXISTS update_all_tender_statuses() CASCADE;

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
    -- ВАЖНО: Порядок имеет значение! Сначала проверяем более специфичные условия
    
    -- 1. Обновление статуса "Разыграна" - ПЕРВЫМ (самое специфичное условие)
    -- delivery_end_date IS NOT NULL AND delivery_end_date >= CURRENT_DATE + 90 дней
    WITH updated AS (
        UPDATE reestr_contract_44_fz
        SET status_id = 3
        WHERE delivery_end_date IS NOT NULL
          AND delivery_end_date >= CURRENT_DATE + INTERVAL '90 days'
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_won FROM updated;
    
    -- 2. Обновление статуса "Работа комиссии" - ВТОРЫМ
    -- end_date < CURRENT_DATE 
    -- И end_date >= CURRENT_DATE - 90 дней
    -- И delivery_end_date IS NULL
    -- И НЕ имеет delivery_end_date >= CURRENT_DATE + 90 дней (уже обработано как "Разыграна")
    WITH updated AS (
        UPDATE reestr_contract_44_fz
        SET status_id = 2
        WHERE end_date IS NOT NULL
          AND end_date < CURRENT_DATE
          AND end_date >= CURRENT_DATE - INTERVAL '90 days'
          AND delivery_end_date IS NULL
          AND (status_id IS NULL OR status_id != 3)  -- Не перезаписываем "Разыграна"
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_commission FROM updated;
    
    -- 3. Обновление статуса "Новая" - ТРЕТЬИМ
    -- end_date >= CURRENT_DATE
    -- И НЕ имеет delivery_end_date >= CURRENT_DATE + 90 дней (уже обработано как "Разыграна")
    WITH updated AS (
        UPDATE reestr_contract_44_fz
        SET status_id = 1
        WHERE end_date IS NOT NULL 
          AND end_date >= CURRENT_DATE
          AND (status_id IS NULL OR status_id != 3)  -- Не перезаписываем "Разыграна"
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_new FROM updated;
    
    -- 4. Обновление статуса "Плохие" - ПОСЛЕДНИМ (все остальные)
    -- Все записи, которые не соответствуют ни одному из "хороших" статусов
    WITH updated AS (
        UPDATE reestr_contract_44_fz
        SET status_id = 4
        WHERE NOT (
            -- "Разыграна"
            (delivery_end_date IS NOT NULL AND delivery_end_date >= CURRENT_DATE + INTERVAL '90 days')
            -- ИЛИ "Работа комиссии"
            OR (end_date IS NOT NULL 
                AND end_date < CURRENT_DATE 
                AND end_date >= CURRENT_DATE - INTERVAL '90 days'
                AND delivery_end_date IS NULL)
            -- ИЛИ "Новая"
            OR (end_date IS NOT NULL AND end_date >= CURRENT_DATE)
        )
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_bad FROM updated;
    
    RETURN QUERY SELECT v_updated_new, v_updated_commission, v_updated_won, v_updated_bad;
END;
$$ LANGUAGE plpgsql;

-- Функция для обновления статусов 223ФЗ
CREATE OR REPLACE FUNCTION update_tender_statuses_223fz()
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
    -- 1. Обновление статуса "Разыграна" - ПЕРВЫМ
    -- delivery_end_date IS NOT NULL AND delivery_end_date >= CURRENT_DATE + 90 дней
    WITH updated AS (
        UPDATE reestr_contract_223_fz
        SET status_id = 3
        WHERE delivery_end_date IS NOT NULL
          AND delivery_end_date >= CURRENT_DATE + INTERVAL '90 days'
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_won FROM updated;
    
    -- 2. Обновление статуса "Работа комиссии" - ВТОРЫМ
    -- end_date < CURRENT_DATE 
    -- И end_date >= CURRENT_DATE - 90 дней
    -- И delivery_end_date IS NULL
    WITH updated AS (
        UPDATE reestr_contract_223_fz
        SET status_id = 2
        WHERE end_date IS NOT NULL
          AND end_date < CURRENT_DATE
          AND end_date >= CURRENT_DATE - INTERVAL '90 days'
          AND delivery_end_date IS NULL
          AND (status_id IS NULL OR status_id != 3)  -- Не перезаписываем "Разыграна"
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_commission FROM updated;
    
    -- 3. Обновление статуса "Новая" - ТРЕТЬИМ
    -- end_date >= CURRENT_DATE
    WITH updated AS (
        UPDATE reestr_contract_223_fz
        SET status_id = 1
        WHERE end_date IS NOT NULL 
          AND end_date >= CURRENT_DATE
          AND (status_id IS NULL OR status_id != 3)  -- Не перезаписываем "Разыграна"
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_new FROM updated;
    
    -- 4. Обновление статуса "Плохие" - ПОСЛЕДНИМ (все остальные)
    WITH updated AS (
        UPDATE reestr_contract_223_fz
        SET status_id = 4
        WHERE NOT (
            -- "Разыграна"
            (delivery_end_date IS NOT NULL AND delivery_end_date >= CURRENT_DATE + INTERVAL '90 days')
            -- ИЛИ "Работа комиссии"
            OR (end_date IS NOT NULL 
                AND end_date < CURRENT_DATE 
                AND end_date >= CURRENT_DATE - INTERVAL '90 days'
                AND delivery_end_date IS NULL)
            -- ИЛИ "Новая"
            OR (end_date IS NOT NULL AND end_date >= CURRENT_DATE)
        )
        RETURNING id
    )
    SELECT COUNT(*) INTO v_updated_bad FROM updated;
    
    RETURN QUERY SELECT v_updated_new, v_updated_commission, v_updated_won, v_updated_bad;
END;
$$ LANGUAGE plpgsql;

-- Функция для обновления всех статусов (44ФЗ + 223ФЗ)
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
    v_223fz_new INTEGER;
    v_223fz_commission INTEGER;
    v_223fz_won INTEGER;
    v_223fz_bad INTEGER;
BEGIN
    -- Обновляем статусы для 44ФЗ
    SELECT * INTO v_44fz_new, v_44fz_commission, v_44fz_won, v_44fz_bad
    FROM update_tender_statuses_44fz();
    
    -- Обновляем статусы для 223ФЗ
    SELECT * INTO v_223fz_new, v_223fz_commission, v_223fz_won, v_223fz_bad
    FROM update_tender_statuses_223fz();
    
    -- Возвращаем результаты для 44ФЗ
    RETURN QUERY SELECT 
        'reestr_contract_44_fz'::TEXT,
        v_44fz_new,
        v_44fz_commission,
        v_44fz_won,
        v_44fz_bad;
    
    -- Возвращаем результаты для 223ФЗ
    RETURN QUERY SELECT 
        'reestr_contract_223_fz'::TEXT,
        v_223fz_new,
        v_223fz_commission,
        v_223fz_won,
        v_223fz_bad;
END;
$$ LANGUAGE plpgsql;

-- Комментарии к функциям
COMMENT ON FUNCTION update_tender_statuses_44fz() IS 
'Обновляет статусы закупок 44ФЗ согласно правилам: Новые (end_date >= CURRENT_DATE), Работа комиссии (end_date < CURRENT_DATE AND end_date >= CURRENT_DATE - 90 дней AND delivery_end_date IS NULL), Разыграна (delivery_end_date IS NOT NULL AND delivery_end_date >= CURRENT_DATE + 90 дней), Плохие (все остальные). Все статусы перезаписываются.';

COMMENT ON FUNCTION update_tender_statuses_223fz() IS 
'Обновляет статусы закупок 223ФЗ согласно тем же правилам, что и 44ФЗ. Все статусы перезаписываются.';

COMMENT ON FUNCTION update_all_tender_statuses() IS 
'Обновляет статусы для всех закупок (44ФЗ и 223ФЗ). Возвращает статистику обновлений.';
