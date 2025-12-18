-- Проверка ОКПД торга 0172200002525000618

-- 1. Какой ОКПД код у этого торга?
SELECT 
    r.id,
    r.contract_number,
    r.okpd_id,
    okpd.main_code,
    okpd.sub_code,
    okpd.name as okpd_name
FROM reestr_contract_44_fz r
LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
WHERE r.contract_number = '0172200002525000618';

-- 2. Есть ли этот ОКПД код у пользователя (user_id = 1)?
SELECT 
    user_okpd.id,
    user_okpd.okpd_code,
    user_okpd.category_id,
    cat.name as category_name,
    CASE 
        WHEN user_okpd.category_id = 1 THEN 'В категории 1'
        WHEN user_okpd.category_id IS NULL THEN 'Без категории'
        ELSE 'В другой категории'
    END as status
FROM okpd_from_users user_okpd
LEFT JOIN okpd_categories cat ON user_okpd.category_id = cat.id
WHERE user_okpd.user_id = 1
    AND user_okpd.okpd_code IN (
        SELECT COALESCE(okpd.main_code, okpd.sub_code)
        FROM reestr_contract_44_fz r
        LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
        WHERE r.contract_number = '0172200002525000618'
    );

-- 3. Все ОКПД коды пользователя в категории 1
SELECT 
    user_okpd.okpd_code,
    okpd.name as okpd_name,
    cat.name as category_name
FROM okpd_from_users user_okpd
LEFT JOIN collection_codes_okpd okpd ON (
    okpd.main_code = user_okpd.okpd_code OR okpd.sub_code = user_okpd.okpd_code
)
LEFT JOIN okpd_categories cat ON user_okpd.category_id = cat.id
WHERE user_okpd.user_id = 1 
    AND user_okpd.category_id = 1
ORDER BY user_okpd.okpd_code;

