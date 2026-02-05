-- Добавление поля has_error в таблицу tender_document_matches
-- Для отметки закупок с ошибками обработки файлов

ALTER TABLE tender_document_matches
ADD COLUMN IF NOT EXISTS has_error BOOLEAN DEFAULT FALSE;

-- Комментарий к полю
COMMENT ON COLUMN tender_document_matches.has_error IS 
'Флаг наличия ошибок при обработке файлов: FALSE = ошибок нет, TRUE = есть ошибки открытия/обработки файлов';

-- Индекс для быстрого поиска закупок с ошибками
CREATE INDEX IF NOT EXISTS idx_tender_matches_has_error 
ON tender_document_matches(has_error) 
WHERE has_error = TRUE;
