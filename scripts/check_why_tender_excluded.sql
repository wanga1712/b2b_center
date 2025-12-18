-- Проверка почему торг 0172200002525000618 не попадает в выборку

-- 1. Проверяем сам торг
SELECT 
    r.id,
    r.contract_number,
    r.end_date,
    r.okpd_id,
    r.auction_name,
    okpd.main_code,
    okpd.sub_code,
    okpd.name as okpd_name,
    CASE 
        WHEN r.end_date IS NULL THEN 'NULL'
        WHEN r.end_date >= CURRENT_DATE THEN '>= сегодня (новый)'
        ELSE '< сегодня (разыгранный)'
    END as tender_status
FROM reestr_contract_44_fz r
LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
WHERE r.contract_number = '0172200002525000618';

-- 2. Проверяем статус обработки и is_interesting
SELECT 
    tdm.tender_id,
    tdm.registry_type,
    tdm.processed_at,
    tdm.match_count,
    tdm.is_interesting
FROM tender_document_matches tdm
WHERE tdm.tender_id = 483682 AND tdm.registry_type = '44fz';

-- 3. Проверяем, входит ли ОКПД этого торга в список ОКПД пользователя (user_id = 1)
SELECT 
    r.okpd_id,
    okpd.main_code,
    okpd.sub_code,
    CASE 
        WHEN user_okpd.id IS NOT NULL THEN 'ЕСТЬ в списке пользователя'
        ELSE 'НЕТ в списке пользователя'
    END as in_user_list,
    user_okpd.category_id,
    cat.name as category_name
FROM reestr_contract_44_fz r
LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
LEFT JOIN okpd_from_users user_okpd ON (
    user_okpd.user_id = 1 
    AND (user_okpd.okpd_code = okpd.main_code OR user_okpd.okpd_code = okpd.sub_code)
)
LEFT JOIN okpd_categories cat ON user_okpd.category_id = cat.id
WHERE r.contract_number = '0172200002525000618';

-- 4. Проверяем, содержит ли название стоп-слова
SELECT 
    r.auction_name,
    sw.stop_word,
    CASE 
        WHEN LOWER(r.auction_name) LIKE '%' || LOWER(sw.stop_word) || '%' THEN 'СОДЕРЖИТ стоп-слово'
        ELSE 'НЕ содержит'
    END as stop_word_check
FROM reestr_contract_44_fz r
CROSS JOIN stop_words_names sw
WHERE r.contract_number = '0172200002525000618'
    AND sw.user_id = 1
    AND LOWER(r.auction_name) LIKE '%' || LOWER(sw.stop_word) || '%';

-- 5. Полная проверка всех условий фильтрации
WITH tender_info AS (
    SELECT 
        r.id,
        r.contract_number,
        r.end_date,
        r.okpd_id,
        r.auction_name,
        okpd.main_code,
        okpd.sub_code
    FROM reestr_contract_44_fz r
    LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
    WHERE r.contract_number = '0172200002525000618'
)
SELECT 
    'Условие end_date >= CURRENT_DATE' as condition_name,
    CASE 
        WHEN ti.end_date IS NULL THEN 'ПРОХОДИТ (NULL)'
        WHEN ti.end_date >= CURRENT_DATE THEN 'ПРОХОДИТ'
        ELSE 'НЕ ПРОХОДИТ'
    END as result
FROM tender_info ti
UNION ALL
SELECT 
    'ОКПД в списке пользователя (категория 1)',
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM okpd_from_users user_okpd
            WHERE user_okpd.user_id = 1 
            AND user_okpd.category_id = 1
            AND (user_okpd.okpd_code = ti.main_code OR user_okpd.okpd_code = ti.sub_code)
        ) THEN 'ПРОХОДИТ'
        ELSE 'НЕ ПРОХОДИТ'
    END
FROM tender_info ti
UNION ALL
SELECT 
    'Нет стоп-слов в названии',
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM stop_words_names sw
            WHERE sw.user_id = 1
            AND LOWER(ti.auction_name) LIKE '%' || LOWER(sw.stop_word) || '%'
        ) THEN 'ПРОХОДИТ'
        ELSE 'НЕ ПРОХОДИТ (содержит стоп-слово)'
    END
FROM tender_info ti
UNION ALL
SELECT 
    'is_interesting != FALSE',
    CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM tender_document_matches tdm
            WHERE tdm.tender_id = ti.id 
            AND tdm.registry_type = '44fz'
            AND tdm.is_interesting = FALSE
        ) THEN 'ПРОХОДИТ'
        ELSE 'НЕ ПРОХОДИТ (is_interesting = FALSE)'
    END
FROM tender_info ti;

