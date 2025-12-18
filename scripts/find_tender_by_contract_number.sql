-- Поиск торга по номеру контракта 0172200002525000618

-- Поиск в 44ФЗ:
SELECT 
    r.id,
    r.contract_number,
    r.tender_link,
    r.start_date,
    r.end_date,
    r.auction_name,
    r.initial_price,
    r.final_price,
    c.customer_short_name,
    okpd.main_code as okpd_main_code,
    okpd.sub_code as okpd_sub_code,
    okpd.name as okpd_name,
    tdm.processed_at,
    tdm.match_count,
    tdm.is_interesting
FROM reestr_contract_44_fz r
LEFT JOIN customer c ON r.customer_id = c.id
LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
LEFT JOIN tender_document_matches tdm ON tdm.tender_id = r.id AND tdm.registry_type = '44fz'
WHERE r.contract_number = '0172200002525000618';

-- Поиск в 223ФЗ:
SELECT 
    r.id,
    r.contract_number,
    r.tender_link,
    r.start_date,
    r.end_date,
    r.auction_name,
    r.initial_price,
    r.final_price,
    c.customer_short_name,
    okpd.main_code as okpd_main_code,
    okpd.sub_code as okpd_sub_code,
    okpd.name as okpd_name,
    tdm.processed_at,
    tdm.match_count,
    tdm.is_interesting
FROM reestr_contract_223_fz r
LEFT JOIN customer c ON r.customer_id = c.id
LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
LEFT JOIN tender_document_matches tdm ON tdm.tender_id = r.id AND tdm.registry_type = '223fz'
WHERE r.contract_number = '0172200002525000618';

-- Поиск в обеих таблицах одновременно:
SELECT 
    r.id,
    r.contract_number,
    r.tender_link,
    r.start_date,
    r.end_date,
    r.auction_name,
    r.initial_price,
    r.final_price,
    c.customer_short_name,
    okpd.main_code as okpd_main_code,
    okpd.sub_code as okpd_sub_code,
    okpd.name as okpd_name,
    '44fz' as registry_type,
    tdm.processed_at,
    tdm.match_count,
    tdm.is_interesting
FROM reestr_contract_44_fz r
LEFT JOIN customer c ON r.customer_id = c.id
LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
LEFT JOIN tender_document_matches tdm ON tdm.tender_id = r.id AND tdm.registry_type = '44fz'
WHERE r.contract_number = '0172200002525000618'
UNION ALL
SELECT 
    r.id,
    r.contract_number,
    r.tender_link,
    r.start_date,
    r.end_date,
    r.auction_name,
    r.initial_price,
    r.final_price,
    c.customer_short_name,
    okpd.main_code as okpd_main_code,
    okpd.sub_code as okpd_sub_code,
    okpd.name as okpd_name,
    '223fz' as registry_type,
    tdm.processed_at,
    tdm.match_count,
    tdm.is_interesting
FROM reestr_contract_223_fz r
LEFT JOIN customer c ON r.customer_id = c.id
LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
LEFT JOIN tender_document_matches tdm ON tdm.tender_id = r.id AND tdm.registry_type = '223fz'
WHERE r.contract_number = '0172200002525000618';

