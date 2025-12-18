-- SQL запрос для получения новых торгов 44ФЗ
-- Замените значения параметров на актуальные для вашего пользователя

-- Параметры (замените на ваши значения):
-- :user_id - ID пользователя (например, 1)
-- :okpd_ids - список ID ОКПД кодов через запятую (например, 1,2,3,4,5)
-- :today - текущая дата в формате 'YYYY-MM-DD' (например, '2025-11-27')
-- :limit - лимит записей (например, 1000)

-- ============================================================================
-- SELECT запрос для получения данных новых торгов 44ФЗ
-- ============================================================================

WITH user_okpd_ids AS (
    -- Здесь укажите ID ОКПД кодов пользователя
    SELECT unnest(ARRAY[1, 2, 3, 4, 5]) AS okpd_id  -- ЗАМЕНИТЕ на ваши okpd_id
),
today_date AS (
    SELECT CURRENT_DATE AS today
)
SELECT DISTINCT
    r.id,
    r.contract_number,
    r.tender_link,
    r.start_date,
    r.end_date,
    r.delivery_start_date,
    r.delivery_end_date,
    r.auction_name,
    r.initial_price,
    r.final_price,
    r.guarantee_amount,
    r.customer_id,
    r.contractor_id,
    r.trading_platform_id,
    r.okpd_id,
    r.region_id,
    r.delivery_region,
    r.delivery_address,
    c.customer_short_name,
    c.customer_full_name,
    reg.name as region_name,
    reg.code as region_code,
    cont.short_name as contractor_short_name,
    cont.full_name as contractor_full_name,
    okpd.main_code as okpd_main_code,
    okpd.sub_code as okpd_sub_code,
    okpd.name as okpd_name,
    tp.trading_platform_name as platform_name,
    tp.trading_platform_url as platform_url,
    c.customer_short_name as balance_holder_name,
    c.customer_inn as balance_holder_inn,
    tdm.processed_at
FROM reestr_contract_44_fz r
LEFT JOIN customer c ON r.customer_id = c.id
LEFT JOIN region reg ON r.region_id = reg.id
LEFT JOIN contractor cont ON r.contractor_id = cont.id
LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
LEFT JOIN trading_platform tp ON r.trading_platform_id = tp.id
LEFT JOIN tender_document_matches tdm ON tdm.tender_id = r.id AND tdm.registry_type = '44fz'
CROSS JOIN today_date td
CROSS JOIN user_okpd_ids uok
WHERE 1=1
    -- Фильтр для новых торгов (end_date >= сегодня или NULL)
    AND (r.end_date IS NULL OR r.end_date >= td.today)
    -- Фильтр по ОКПД кодам пользователя
    AND r.okpd_id = uok.okpd_id
    -- Фильтр для исключения неинтересных тендеров (is_interesting = FALSE)
    AND NOT EXISTS (
        SELECT 1 FROM tender_document_matches tdm_filter
        WHERE tdm_filter.tender_id = r.id 
        AND tdm_filter.registry_type = '44fz'
        AND tdm_filter.is_interesting = FALSE
    )
    -- Добавьте фильтр по региону, если нужно:
    -- AND r.region_id = :region_id
    -- Добавьте фильтр по стоп-словам, если нужно:
    -- AND LOWER(r.auction_name) NOT LIKE '%стоп-слово%'
ORDER BY tdm.processed_at DESC NULLS LAST, r.start_date DESC, r.id DESC
LIMIT 1000;  -- ЗАМЕНИТЕ на нужный лимит

-- ============================================================================
-- COUNT запрос для получения количества новых торгов 44ФЗ
-- ============================================================================

WITH user_okpd_ids AS (
    -- Здесь укажите ID ОКПД кодов пользователя
    SELECT unnest(ARRAY[1, 2, 3, 4, 5]) AS okpd_id  -- ЗАМЕНИТЕ на ваши okpd_id
),
today_date AS (
    SELECT CURRENT_DATE AS today
)
SELECT COUNT(DISTINCT r.id) as total_count
FROM reestr_contract_44_fz r
LEFT JOIN customer c ON r.customer_id = c.id
LEFT JOIN region reg ON r.region_id = reg.id
LEFT JOIN contractor cont ON r.contractor_id = cont.id
LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
LEFT JOIN trading_platform tp ON r.trading_platform_id = tp.id
LEFT JOIN tender_document_matches tdm ON tdm.tender_id = r.id AND tdm.registry_type = '44fz'
CROSS JOIN today_date td
CROSS JOIN user_okpd_ids uok
WHERE 1=1
    -- Фильтр для новых торгов (end_date >= сегодня или NULL)
    AND (r.end_date IS NULL OR r.end_date >= td.today)
    -- Фильтр по ОКПД кодам пользователя
    AND r.okpd_id = uok.okpd_id
    -- Фильтр для исключения неинтересных тендеров (is_interesting = FALSE)
    AND NOT EXISTS (
        SELECT 1 FROM tender_document_matches tdm_filter
        WHERE tdm_filter.tender_id = r.id 
        AND tdm_filter.registry_type = '44fz'
        AND tdm_filter.is_interesting = FALSE
    );

-- ============================================================================
-- Как получить ID ОКПД кодов пользователя:
-- ============================================================================

-- SELECT okpd_code FROM okpd_from_users WHERE user_id = 1;

-- ============================================================================
-- Как получить ID ОКПД из collection_codes_okpd по кодам:
-- ============================================================================

-- SELECT id FROM collection_codes_okpd 
-- WHERE main_code IN ('код1', 'код2') OR sub_code IN ('код1', 'код2');

