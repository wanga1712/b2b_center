-- Оптимизированный SQL запрос для новых торгов 44ФЗ
-- Замените: 1 на ваш user_id, 1 на category_id

-- Оптимизация: используем CTE для предварительной выборки okpd_ids и стоп-слов
WITH user_okpd_ids AS (
    -- Получаем ID ОКПД кодов пользователя из выбранной категории
    SELECT DISTINCT okpd_table.id
    FROM okpd_from_users user_okpd
    JOIN collection_codes_okpd okpd_table ON (
        okpd_table.main_code = user_okpd.okpd_code 
        OR okpd_table.sub_code = user_okpd.okpd_code
    )
    WHERE user_okpd.user_id = 1  -- ЗАМЕНИТЕ на ваш user_id
        AND user_okpd.category_id = 1  -- ЗАМЕНИТЕ на category_id или уберите для всех категорий
),
user_stop_words AS (
    -- Получаем стоп-слова пользователя
    SELECT LOWER(stop_word) as stop_word
    FROM stop_words_names
    WHERE user_id = 1  -- ЗАМЕНИТЕ на ваш user_id
)
SELECT COUNT(DISTINCT r.id) as total_count
FROM reestr_contract_44_fz r
WHERE (r.end_date IS NULL OR r.end_date >= CURRENT_DATE)
    AND r.okpd_id IN (SELECT id FROM user_okpd_ids)
    -- Фильтр по стоп-словам (быстрее через NOT EXISTS)
    AND NOT EXISTS (
        SELECT 1 FROM user_stop_words sw
        WHERE LOWER(r.auction_name) LIKE '%' || sw.stop_word || '%'
    )
    -- Фильтр для исключения неинтересных тендеров
    AND NOT EXISTS (
        SELECT 1 FROM tender_document_matches tdm_filter
        WHERE tdm_filter.tender_id = r.id 
        AND tdm_filter.registry_type = '44fz'
        AND tdm_filter.is_interesting = FALSE
    );

-- Список названий аукционов (оптимизированный)
WITH user_okpd_ids AS (
    SELECT DISTINCT okpd_table.id
    FROM okpd_from_users user_okpd
    JOIN collection_codes_okpd okpd_table ON (
        okpd_table.main_code = user_okpd.okpd_code 
        OR okpd_table.sub_code = user_okpd.okpd_code
    )
    WHERE user_okpd.user_id = 1  -- ЗАМЕНИТЕ на ваш user_id
        AND user_okpd.category_id = 1  -- ЗАМЕНИТЕ на category_id или уберите для всех категорий
),
user_stop_words AS (
    SELECT LOWER(stop_word) as stop_word
    FROM stop_words_names
    WHERE user_id = 1  -- ЗАМЕНИТЕ на ваш user_id
)
SELECT DISTINCT r.auction_name
FROM reestr_contract_44_fz r
WHERE (r.end_date IS NULL OR r.end_date >= CURRENT_DATE)
    AND r.okpd_id IN (SELECT id FROM user_okpd_ids)
    AND NOT EXISTS (
        SELECT 1 FROM user_stop_words sw
        WHERE LOWER(r.auction_name) LIKE '%' || sw.stop_word || '%'
    )
    AND NOT EXISTS (
        SELECT 1 FROM tender_document_matches tdm_filter
        WHERE tdm_filter.tender_id = r.id 
        AND tdm_filter.registry_type = '44fz'
        AND tdm_filter.is_interesting = FALSE
    )
ORDER BY r.auction_name;

