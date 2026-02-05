-- Создание таблицы для отслеживания обработанных торгов
CREATE TABLE IF NOT EXISTS processed_tenders (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER NOT NULL,
    registry_type VARCHAR(10) NOT NULL, -- '44fz' или '223fz'
    folder_name VARCHAR(255) NOT NULL, -- имя папки/директории
    processing_status VARCHAR(50) NOT NULL DEFAULT 'completed', -- 'completed', 'failed', 'in_progress'
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    machine_id VARCHAR(100), -- ID машины для параллельной обработки
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Уникальный индекс для предотвращения дублирования
    UNIQUE(tender_id, registry_type, folder_name)
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_processed_tenders_tender ON processed_tenders (tender_id, registry_type);
CREATE INDEX IF NOT EXISTS idx_processed_tenders_status ON processed_tenders (processing_status);
CREATE INDEX IF NOT EXISTS idx_processed_tenders_machine ON processed_tenders (machine_id);
CREATE INDEX IF NOT EXISTS idx_processed_tenders_user ON processed_tenders (user_id);
CREATE INDEX IF NOT EXISTS idx_processed_tenders_folder ON processed_tenders (folder_name);

-- Таблица для отслеживания обработанных файлов
CREATE TABLE IF NOT EXISTS processed_files (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER NOT NULL,
    registry_type VARCHAR(10) NOT NULL,
    file_path TEXT NOT NULL, -- полный путь к файлу
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT,
    processing_status VARCHAR(50) NOT NULL DEFAULT 'completed',
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    machine_id VARCHAR(100),
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Уникальный индекс для файлов
    UNIQUE(tender_id, registry_type, file_path)
);

-- Индексы для processed_files
CREATE INDEX IF NOT EXISTS idx_processed_files_tender ON processed_files (tender_id, registry_type);
CREATE INDEX IF NOT EXISTS idx_processed_files_status ON processed_files (processing_status);
CREATE INDEX IF NOT EXISTS idx_processed_files_machine ON processed_files (machine_id);

-- Комментарии
COMMENT ON TABLE processed_tenders IS 'Таблица обработанных торгов для предотвращения повторной обработки';
COMMENT ON TABLE processed_files IS 'Таблица обработанных файлов для отслеживания прогресса';
COMMENT ON COLUMN processed_tenders.machine_id IS 'ID машины для поддержки параллельной обработки на разных серверах';
COMMENT ON COLUMN processed_files.file_size IS 'Размер файла в байтах для статистики';
