-- SQL запрос для получения новых торгов 44ФЗ с использованием ОКПД пользователя
-- Замените :user_id на ID вашего пользователя (например, 1)

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
WHERE 1=1
    -- Фильтр для новых торгов (end_date >= сегодня или NULL)
    AND (r.end_date IS NULL OR r.end_date >= CURRENT_DATE)
    -- Фильтр по ОКПД кодам пользователя (берем из okpd_from_users и ищем в collection_codes_okpd)
    AND r.okpd_id IN (
        SELECT DISTINCT okpd_table.id
        FROM okpd_from_users user_okpd
        JOIN collection_codes_okpd okpd_table ON (
            okpd_table.main_code = user_okpd.okpd_code 
            OR okpd_table.sub_code = user_okpd.okpd_code
        )
        WHERE user_okpd.user_id = 1  -- ЗАМЕНИТЕ на ваш user_id
    )
    -- Фильтр для исключения неинтересных тендеров (is_interesting = FALSE)
    AND NOT EXISTS (
        SELECT 1 FROM tender_document_matches tdm_filter
        WHERE tdm_filter.tender_id = r.id 
        AND tdm_filter.registry_type = '44fz'
        AND tdm_filter.is_interesting = FALSE
    )
ORDER BY tdm.processed_at DESC NULLS LAST, r.start_date DESC, r.id DESC
LIMIT 1000;

-- COUNT запрос:
SELECT COUNT(DISTINCT r.id) as total_count
FROM reestr_contract_44_fz r
LEFT JOIN customer c ON r.customer_id = c.id
LEFT JOIN region reg ON r.region_id = reg.id
LEFT JOIN contractor cont ON r.contractor_id = cont.id
LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
LEFT JOIN trading_platform tp ON r.trading_platform_id = tp.id
LEFT JOIN tender_document_matches tdm ON tdm.tender_id = r.id AND tdm.registry_type = '44fz'
WHERE 1=1
    AND (r.end_date IS NULL OR r.end_date >= CURRENT_DATE)
    AND r.okpd_id IN (
        SELECT DISTINCT okpd_table.id
        FROM okpd_from_users user_okpd
        JOIN collection_codes_okpd okpd_table ON (
            okpd_table.main_code = user_okpd.okpd_code 
            OR okpd_table.sub_code = user_okpd.okpd_code
        )
        WHERE user_okpd.user_id = 1  -- ЗАМЕНИТЕ на ваш user_id
    )
    AND NOT EXISTS (
        SELECT 1 FROM tender_document_matches tdm_filter
        WHERE tdm_filter.tender_id = r.id 
        AND tdm_filter.registry_type = '44fz'
        AND tdm_filter.is_interesting = FALSE
    );

