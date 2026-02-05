-- Добавление поля folder_name в таблицу tender_document_matches
-- для отслеживания обработанных папок и предотвращения повторной обработки

-- Добавляем поле folder_name
ALTER TABLE tender_document_matches 
ADD COLUMN IF NOT EXISTS folder_name VARCHAR(255);

-- Добавляем индекс для быстрого поиска по folder_name
CREATE INDEX IF NOT EXISTS idx_tender_matches_folder_name 
ON tender_document_matches(folder_name) 
WHERE folder_name IS NOT NULL;

-- Комментарий к полю
COMMENT ON COLUMN tender_document_matches.folder_name IS 
'Название папки с файлами закупки (например: 44fz_12345 или 44fz_12345_won). Используется для предотвращения повторной обработки файлов.';

