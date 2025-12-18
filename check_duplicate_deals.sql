-- Безопасная проверка дубликатов сделок для закупки 518801
-- Сначала просто посмотрим все записи
SELECT 
    id,
    pipeline_type,
    stage_id,
    tender_id,
    name,
    description,
    amount,
    margin,
    status,
    tender_status_id,
    user_id,
    created_at,
    updated_at,
    metadata
FROM sales_deals
WHERE tender_id = 518801
  AND pipeline_type = 'materials_supply'
  AND user_id = 1
ORDER BY id;

-- Теперь сравним все поля между записями (кроме id, created_at, updated_at)
-- Этот запрос покажет, какие пары записей полностью идентичны
WITH deals AS (
    SELECT 
        id,
        pipeline_type,
        stage_id,
        tender_id,
        name,
        description,
        amount,
        margin,
        status,
        tender_status_id,
        user_id,
        metadata
    FROM sales_deals
    WHERE tender_id = 518801
      AND pipeline_type = 'materials_supply'
      AND user_id = 1
)
SELECT
    a.id AS id1,
    b.id AS id2,
    -- Проверяем совпадение каждого поля
    CASE 
        WHEN a.pipeline_type = b.pipeline_type 
         AND a.stage_id = b.stage_id
         AND a.tender_id = b.tender_id
         AND a.name = b.name
         AND COALESCE(a.description, '') = COALESCE(b.description, '')
         AND COALESCE(a.amount::text, '') = COALESCE(b.amount::text, '')
         AND COALESCE(a.margin::text, '') = COALESCE(b.margin::text, '')
         AND a.status = b.status
         AND COALESCE(a.tender_status_id::text, '') = COALESCE(b.tender_status_id::text, '')
         AND a.user_id = b.user_id
         AND COALESCE(a.metadata::text, '{}') = COALESCE(b.metadata::text, '{}')
        THEN true
        ELSE false
    END AS all_fields_equal
FROM deals a
JOIN deals b ON a.id < b.id
ORDER BY a.id, b.id;

-- ============================================================================
-- ПОИСК ДУБЛЕЙ ПО ВСЕЙ БАЗЕ ДАННЫХ
-- ============================================================================

-- ЗАПРОС 1: Найти все группы дублей (записи, которые отличаются только id, created_at, updated_at, metadata.last_sync)
WITH normalized AS (
    SELECT
        id,
        pipeline_type,
        stage_id,
        tender_id,
        name,
        description,
        amount,
        margin,
        status,
        tender_status_id,
        user_id,
        -- Нормализуем metadata: выкидываем last_sync, NULL → пустой объект
        COALESCE((metadata::jsonb - 'last_sync'), '{}'::jsonb) AS meta_norm,
        created_at,
        updated_at
    FROM sales_deals
),
dupe_groups AS (
    SELECT
        pipeline_type,
        stage_id,
        tender_id,
        name,
        description,
        amount,
        margin,
        status,
        tender_status_id,
        user_id,
        meta_norm,
        COUNT(*) AS deals_count,
        ARRAY_AGG(id ORDER BY id)        AS ids,
        MIN(created_at)                  AS first_created_at,
        MAX(created_at)                  AS last_created_at
    FROM normalized
    GROUP BY
        pipeline_type,
        stage_id,
        tender_id,
        name,
        description,
        amount,
        margin,
        status,
        tender_status_id,
        user_id,
        meta_norm
    HAVING COUNT(*) > 1
)
SELECT
    pipeline_type,
    stage_id,
    tender_id,
    name,
    deals_count,
    ids,
    first_created_at,
    last_created_at
FROM dupe_groups
ORDER BY deals_count DESC, tender_id, stage_id;

-- ЗАПРОС 2: Общая статистика по дублям (более понятный вывод)
WITH normalized AS (
    SELECT
        id,
        pipeline_type,
        stage_id,
        tender_id,
        name,
        description,
        amount,
        margin,
        status,
        tender_status_id,
        user_id,
        COALESCE((metadata::jsonb - 'last_sync'), '{}'::jsonb) AS meta_norm
    FROM sales_deals
),
dupe_groups AS (
    SELECT
        pipeline_type,
        stage_id,
        tender_id,
        name,
        description,
        amount,
        margin,
        status,
        tender_status_id,
        user_id,
        meta_norm,
        COUNT(*) AS deals_count
    FROM normalized
    GROUP BY
        pipeline_type,
        stage_id,
        tender_id,
        name,
        description,
        amount,
        margin,
        status,
        tender_status_id,
        user_id,
        meta_norm
    HAVING COUNT(*) > 1
)
SELECT
    'Найдено групп дублей:' AS description,
    COUNT(*)::text AS value
FROM dupe_groups
UNION ALL
SELECT
    'Всего записей в группах дублей:' AS description,
    SUM(deals_count)::text AS value
FROM dupe_groups
UNION ALL
SELECT
    'Записей можно удалить (оставив по 1 в каждой группе):' AS description,
    (SUM(deals_count) - COUNT(*))::text AS value
FROM dupe_groups;

