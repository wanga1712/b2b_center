-- Пометить торг 0172200002525000618 как необработанный
-- Удаляем запись из tender_document_matches, чтобы система считала его необработанным

-- 1. Проверяем текущую запись
SELECT 
    tdm.id,
    tdm.tender_id,
    tdm.registry_type,
    tdm.processed_at,
    tdm.match_count,
    tdm.is_interesting
FROM tender_document_matches tdm
WHERE tdm.tender_id = 483682 AND tdm.registry_type = '44fz';

-- 2. Удаляем запись из tender_document_matches (помечаем как необработанный)
DELETE FROM tender_document_matches
WHERE tender_id = 483682 AND registry_type = '44fz';

-- 3. Удаляем детали совпадений (если есть)
DELETE FROM tender_document_match_details
WHERE match_id IN (
    SELECT id FROM tender_document_matches 
    WHERE tender_id = 483682 AND registry_type = '44fz'
);

-- 4. Проверяем, что запись удалена
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'Торг помечен как необработанный (запись удалена)'
        ELSE 'Ошибка: запись все еще существует'
    END as status
FROM tender_document_matches
WHERE tender_id = 483682 AND registry_type = '44fz';

