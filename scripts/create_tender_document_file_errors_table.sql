-- Создание таблицы для хранения информации об ошибках обработки файлов

CREATE TABLE IF NOT EXISTS tender_document_file_errors (
    id SERIAL PRIMARY KEY,
    
    -- Связь с результатом обработки
    match_id INTEGER NOT NULL REFERENCES tender_document_matches(id) ON DELETE CASCADE,
    
    -- Информация о проблемном файле
    file_path TEXT NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    file_size_mb NUMERIC(10, 2),
    
    -- Информация об ошибке
    error_message TEXT NOT NULL,
    error_type VARCHAR(100),  -- 'open_error', 'parse_error', 'timeout', 'cuda_error', etc.
    
    -- Дополнительная информация
    processing_time_seconds NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Уникальность: один файл = одна запись ошибки для каждого match_id
    CONSTRAINT unique_file_error UNIQUE (match_id, file_path)
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_file_errors_match_id ON tender_document_file_errors(match_id);
CREATE INDEX IF NOT EXISTS idx_file_errors_error_type ON tender_document_file_errors(error_type);
CREATE INDEX IF NOT EXISTS idx_file_errors_file_name ON tender_document_file_errors(file_name);

-- Комментарии к таблице и полям
COMMENT ON TABLE tender_document_file_errors IS 'Информация об ошибках обработки файлов для закупок';
COMMENT ON COLUMN tender_document_file_errors.match_id IS 'ID записи результата обработки из tender_document_matches';
COMMENT ON COLUMN tender_document_file_errors.file_path IS 'Полный путь к проблемному файлу';
COMMENT ON COLUMN tender_document_file_errors.file_name IS 'Имя проблемного файла';
COMMENT ON COLUMN tender_document_file_errors.error_message IS 'Подробное описание ошибки';
COMMENT ON COLUMN tender_document_file_errors.error_type IS 'Тип ошибки: open_error, parse_error, timeout, cuda_error, etc.';
