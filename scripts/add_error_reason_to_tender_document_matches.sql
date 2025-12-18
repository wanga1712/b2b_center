-- Добавление поля error_reason в таблицу tender_document_matches
-- Для хранения информации об ошибках обработки закупок

ALTER TABLE tender_document_matches
ADD COLUMN IF NOT EXISTS error_reason TEXT;

-- Комментарий к полю
COMMENT ON COLUMN tender_document_matches.error_reason IS 
'Причина ошибки обработки: NULL = обработано успешно, текст = описание ошибки (например, "no_documents", "file_open_error", "processing_timeout")';

-- Индекс для быстрого поиска закупок с ошибками
CREATE INDEX IF NOT EXISTS idx_tender_matches_error_reason 
ON tender_document_matches(error_reason) 
WHERE error_reason IS NOT NULL;

