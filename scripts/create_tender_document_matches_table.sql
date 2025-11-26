-- Создание таблицы для хранения результатов поиска совпадений в документации торгов
-- Связь с реестрами контрактов 44-ФЗ и 223-ФЗ

CREATE TABLE IF NOT EXISTS tender_document_matches (
    id SERIAL PRIMARY KEY,
    
    -- Связь с торгом
    tender_id INTEGER NOT NULL,
    registry_type VARCHAR(10) NOT NULL CHECK (registry_type IN ('44fz', '223fz')),
    
    -- Результаты поиска
    match_count INTEGER NOT NULL DEFAULT 0,
    match_percentage NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    -- match_percentage: 100.00 = 100% совпадений, 85.00 = 85% совпадений, 0.00 = не обработано
    
    -- Статус интереса пользователя
    is_interesting BOOLEAN DEFAULT NULL,
    -- NULL = не установлен, TRUE = интересно, FALSE = неинтересно
    
    -- Детали обработки
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_time_seconds NUMERIC(10, 2),
    
    -- Дополнительная информация
    total_files_processed INTEGER DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,
    
    -- Уникальность: один торг = одна запись результатов
    CONSTRAINT unique_tender_match UNIQUE (tender_id, registry_type)
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_tender_matches_registry_type ON tender_document_matches(registry_type);
CREATE INDEX IF NOT EXISTS idx_tender_matches_match_percentage ON tender_document_matches(match_percentage);
CREATE INDEX IF NOT EXISTS idx_tender_matches_is_interesting ON tender_document_matches(is_interesting);
CREATE INDEX IF NOT EXISTS idx_tender_matches_processed_at ON tender_document_matches(processed_at);

-- Комментарии к таблице и полям
COMMENT ON TABLE tender_document_matches IS 'Результаты поиска совпадений товаров в документации торгов';
COMMENT ON COLUMN tender_document_matches.tender_id IS 'ID торга из реестра контрактов';
COMMENT ON COLUMN tender_document_matches.registry_type IS 'Тип реестра: 44fz или 223fz';
COMMENT ON COLUMN tender_document_matches.match_count IS 'Количество найденных совпадений товаров';
COMMENT ON COLUMN tender_document_matches.match_percentage IS 'Процент совпадений: 100.00 = 100%, 85.00 = 85%, 0.00 = не обработано';
COMMENT ON COLUMN tender_document_matches.is_interesting IS 'Статус интереса пользователя: NULL = не установлен, TRUE = интересно, FALSE = неинтересно';
COMMENT ON COLUMN tender_document_matches.processed_at IS 'Дата и время обработки документов';
COMMENT ON COLUMN tender_document_matches.processing_time_seconds IS 'Время обработки в секундах';
COMMENT ON COLUMN tender_document_matches.total_files_processed IS 'Общее количество обработанных файлов';
COMMENT ON COLUMN tender_document_matches.total_size_bytes IS 'Общий размер обработанных файлов в байтах';

