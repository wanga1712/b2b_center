-- Скрипт для оптимизации запросов к таблицам торгов
-- Создает необходимые индексы для ускорения выборки

-- ============================================
-- ИНДЕКСЫ ДЛЯ reestr_contract_44_fz
-- ============================================

-- Индекс для фильтрации по end_date (для новых и разыгранных торгов)
CREATE INDEX IF NOT EXISTS idx_reestr_44fz_end_date 
ON reestr_contract_44_fz(end_date) 
WHERE end_date IS NOT NULL;

-- Индекс для фильтрации по end_date и delivery_end_date (для разыгранных)
CREATE INDEX IF NOT EXISTS idx_reestr_44fz_end_delivery_dates 
ON reestr_contract_44_fz(end_date, delivery_end_date) 
WHERE end_date IS NOT NULL AND delivery_end_date IS NOT NULL;

-- Индекс для фильтрации по okpd_id (для фильтрации по ОКПД)
CREATE INDEX IF NOT EXISTS idx_reestr_44fz_okpd_id 
ON reestr_contract_44_fz(okpd_id) 
WHERE okpd_id IS NOT NULL;

-- Композитный индекс для основных фильтров (end_date + okpd_id + region_id)
CREATE INDEX IF NOT EXISTS idx_reestr_44fz_main_filters 
ON reestr_contract_44_fz(end_date, okpd_id, region_id) 
WHERE end_date IS NOT NULL;

-- Индекс для сортировки по start_date
CREATE INDEX IF NOT EXISTS idx_reestr_44fz_start_date 
ON reestr_contract_44_fz(start_date DESC);

-- ============================================
-- ИНДЕКСЫ ДЛЯ reestr_contract_223_fz
-- ============================================

-- Индекс для фильтрации по end_date (для новых и разыгранных торгов)
CREATE INDEX IF NOT EXISTS idx_reestr_223fz_end_date 
ON reestr_contract_223_fz(end_date) 
WHERE end_date IS NOT NULL;

-- Индекс для фильтрации по end_date и delivery_end_date (для разыгранных)
CREATE INDEX IF NOT EXISTS idx_reestr_223fz_end_delivery_dates 
ON reestr_contract_223_fz(end_date, delivery_end_date) 
WHERE end_date IS NOT NULL AND delivery_end_date IS NOT NULL;

-- Индекс для фильтрации по okpd_id (для фильтрации по ОКПД)
CREATE INDEX IF NOT EXISTS idx_reestr_223fz_okpd_id 
ON reestr_contract_223_fz(okpd_id) 
WHERE okpd_id IS NOT NULL;

-- Композитный индекс для основных фильтров (end_date + okpd_id + region_id)
CREATE INDEX IF NOT EXISTS idx_reestr_223fz_main_filters 
ON reestr_contract_223_fz(end_date, okpd_id, region_id) 
WHERE end_date IS NOT NULL;

-- Индекс для сортировки по start_date
CREATE INDEX IF NOT EXISTS idx_reestr_223fz_start_date 
ON reestr_contract_223_fz(start_date DESC);

-- ============================================
-- ИНДЕКСЫ ДЛЯ tender_document_matches
-- ============================================

-- Композитный индекс для быстрого поиска по tender_id + registry_type + is_interesting
CREATE INDEX IF NOT EXISTS idx_tdm_tender_registry_interesting 
ON tender_document_matches(tender_id, registry_type, is_interesting) 
WHERE is_interesting = FALSE;

-- Индекс для сортировки по processed_at
CREATE INDEX IF NOT EXISTS idx_tdm_processed_at_desc 
ON tender_document_matches(processed_at DESC NULLS LAST);

-- Композитный индекс для фильтрации и сортировки
CREATE INDEX IF NOT EXISTS idx_tdm_registry_processed 
ON tender_document_matches(registry_type, processed_at DESC NULLS LAST);

-- ============================================
-- ИНДЕКСЫ ДЛЯ collection_codes_okpd
-- ============================================

-- Индекс для поиска по main_code и sub_code
CREATE INDEX IF NOT EXISTS idx_okpd_main_code 
ON collection_codes_okpd(main_code) 
WHERE main_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_okpd_sub_code 
ON collection_codes_okpd(sub_code) 
WHERE sub_code IS NOT NULL;

-- Композитный индекс для поиска по обоим кодам
CREATE INDEX IF NOT EXISTS idx_okpd_codes 
ON collection_codes_okpd(main_code, sub_code);

-- ============================================
-- АНАЛИЗ ТАБЛИЦ (для обновления статистики планировщика)
-- ============================================

-- Обновляем статистику для оптимизатора запросов
ANALYZE reestr_contract_44_fz;
ANALYZE reestr_contract_223_fz;
ANALYZE tender_document_matches;
ANALYZE collection_codes_okpd;

