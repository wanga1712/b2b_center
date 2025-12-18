-- Оптимизация индексов для ускорения запросов ОКПД и тендеров
-- Выполнить на БД tender_monitor

-- Индексы для таблицы collection_codes_okpd (если их еще нет)
CREATE INDEX IF NOT EXISTS idx_okpd_main_code ON collection_codes_okpd(main_code);
CREATE INDEX IF NOT EXISTS idx_okpd_sub_code ON collection_codes_okpd(sub_code);
CREATE INDEX IF NOT EXISTS idx_okpd_name_lower ON collection_codes_okpd(LOWER(name));

-- Индексы для таблицы reestr_contract_44_fz (для фильтрации по региону и ОКПД)
CREATE INDEX IF NOT EXISTS idx_44fz_okpd_region ON reestr_contract_44_fz(okpd_id, region_id);
CREATE INDEX IF NOT EXISTS idx_44fz_region ON reestr_contract_44_fz(region_id);
CREATE INDEX IF NOT EXISTS idx_44fz_end_date ON reestr_contract_44_fz(end_date);
CREATE INDEX IF NOT EXISTS idx_44fz_delivery_end_date ON reestr_contract_44_fz(delivery_end_date);

-- Индексы для таблицы reestr_contract_223_fz (для фильтрации по региону и ОКПД)
CREATE INDEX IF NOT EXISTS idx_223fz_okpd_region ON reestr_contract_223_fz(okpd_id, region_id);
CREATE INDEX IF NOT EXISTS idx_223fz_region ON reestr_contract_223_fz(region_id);
CREATE INDEX IF NOT EXISTS idx_223fz_end_date ON reestr_contract_223_fz(end_date);
CREATE INDEX IF NOT EXISTS idx_223fz_delivery_end_date ON reestr_contract_223_fz(delivery_end_date);

-- Индексы для таблицы tender_document_matches (для фильтрации is_interesting)
CREATE INDEX IF NOT EXISTS idx_tdm_tender_registry ON tender_document_matches(tender_id, registry_type);
CREATE INDEX IF NOT EXISTS idx_tdm_is_interesting ON tender_document_matches(is_interesting) WHERE is_interesting = FALSE;
CREATE INDEX IF NOT EXISTS idx_tdm_processed_at ON tender_document_matches(processed_at);

-- Композитный индекс для быстрого поиска неинтересных тендеров
CREATE INDEX IF NOT EXISTS idx_tdm_tender_registry_interesting ON tender_document_matches(tender_id, registry_type, is_interesting) WHERE is_interesting = FALSE;

-- Анализ таблиц для обновления статистики планировщика
ANALYZE collection_codes_okpd;
ANALYZE reestr_contract_44_fz;
ANALYZE reestr_contract_223_fz;
ANALYZE tender_document_matches;

