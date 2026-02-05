# Техническое описание системы поиска торгов и анализа документации

## 📋 Оглавление

1. [Обзор системы](#обзор-системы)
2. [Структура базы данных](#структура-базы-данных)
3. [Логика поиска торгов](#логика-поиска-торгов)
4. [Логика анализа документации](#логика-анализа-документации)
5. [SQL запросы](#sql-запросы)
6. [API эндпоинты (рекомендации)](#api-эндпоинты-рекомендации)

---

## Обзор системы

Система предназначена для:
- **Поиска торгов** по критериям пользователя (OKPD коды, стоп-слова, регион, статус)
- **Анализа документации** торгов на предмет совпадений с товарами из каталога
- **Фильтрации** нерелевантных торгов по стоп-словам и флагам интереса

### Основные компоненты

1. **Поиск торгов** - фильтрация по OKPD, стоп-словам, статусам
2. **Анализ документации** - скачивание, распаковка, поиск совпадений
3. **Хранение результатов** - сохранение найденных совпадений в БД

---

## Структура базы данных

### База данных: `tender_monitor` (PostgreSQL)

#### Основные таблицы торгов

##### `reestr_contract_44_fz` (44-ФЗ)
```sql
CREATE TABLE reestr_contract_44_fz (
    id INTEGER PRIMARY KEY,
    auction_name VARCHAR(500),           -- Название аукциона
    start_date DATE,                      -- Дата начала
    end_date DATE,                        -- Дата окончания
    delivery_end_date DATE,               -- Дата окончания поставки
    status_id INTEGER,                    -- Статус торга (1=Новая, 2=Работа комиссии, 3=Разыграна)
    okpd_id INTEGER,                      -- FK к collection_codes_okpd
    customer_id INTEGER,                  -- FK к customer
    region_id INTEGER,                    -- FK к region
    contractor_id INTEGER,               -- FK к contractor
    trading_platform_id INTEGER,         -- FK к trading_platform
    -- ... другие поля
);
```

##### `reestr_contract_223_fz` (223-ФЗ)
Аналогичная структура для 223-ФЗ.

#### Таблицы настроек пользователя

##### `okpd_from_users` - ОКПД коды пользователя
```sql
CREATE TABLE okpd_from_users (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    okpd_code VARCHAR(50) NOT NULL,      -- Код ОКПД (например, "41.20.10.000")
    name VARCHAR(500),                    -- Название (опционально)
    category_id INTEGER,                  -- FK к okpd_categories
    setting_id INTEGER,                   -- FK к user_search_settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

##### `okpd_categories` - Категории ОКПД
```sql
CREATE TABLE okpd_categories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,           -- Название категории (например, "Строительные материалы")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

##### `collection_codes_okpd` - Справочник ОКПД кодов
```sql
CREATE TABLE collection_codes_okpd (
    id INTEGER PRIMARY KEY,
    main_code VARCHAR(50),               -- Основной код ОКПД
    sub_code VARCHAR(50),                  -- Подкод ОКПД
    name VARCHAR(500)                     -- Название
);
```

**Связь:** `okpd_from_users.okpd_code` сопоставляется с `collection_codes_okpd.main_code` или `collection_codes_okpd.sub_code`

##### `stop_words_names` - Стоп-слова пользователя
```sql
CREATE TABLE stop_words_names (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    stop_word VARCHAR(500) NOT NULL,      -- Фраза для исключения (например, "системы вентиляции")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

##### `user_search_settings` - Настройки поиска
```sql
CREATE TABLE user_search_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    region_id INTEGER,                    -- FK к region (опционально)
    -- ... другие настройки
);
```

#### Таблицы результатов анализа

##### `tender_document_matches` - Результаты анализа
```sql
CREATE TABLE tender_document_matches (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER NOT NULL,
    registry_type VARCHAR(10) NOT NULL,   -- '44fz' или '223fz'
    folder_name VARCHAR(255),             -- Имя папки с документами
    match_count INTEGER DEFAULT 0,        -- Количество найденных совпадений
    match_percentage DECIMAL(5,2),        -- Процент совпадения
    is_interesting BOOLEAN DEFAULT TRUE,  -- Флаг интереса (FALSE = исключить из поиска)
    processed_at TIMESTAMP,               -- Дата обработки
    processing_time_seconds DECIMAL(10,2), -- Время обработки
    total_file_size_bytes BIGINT,         -- Общий размер обработанных файлов
    error_reason TEXT,                    -- Причина ошибки (если есть)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(tender_id, registry_type)
);
```

##### `tender_document_match_details` - Детали совпадений
```sql
CREATE TABLE tender_document_match_details (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL,            -- FK к tender_document_matches
    product_name VARCHAR(500),             -- Название товара из каталога
    file_path TEXT,                        -- Путь к файлу
    sheet_name VARCHAR(255),               -- Название листа Excel
    row_number INTEGER,                    -- Номер строки
    cell_address VARCHAR(50),              -- Адрес ячейки (например, "A5")
    match_score DECIMAL(5,2),              -- Оценка совпадения (0-100)
    context_text TEXT,                    -- Контекст найденного текста
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Справочные таблицы

##### `customer` - Заказчики
```sql
CREATE TABLE customer (
    id INTEGER PRIMARY KEY,
    short_name VARCHAR(500),
    full_name VARCHAR(1000),
    inn VARCHAR(20)
);
```

##### `region` - Регионы
```sql
CREATE TABLE region (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255),
    code VARCHAR(10)
);
```

##### `contractor` - Подрядчики
```sql
CREATE TABLE contractor (
    id INTEGER PRIMARY KEY,
    short_name VARCHAR(500),
    full_name VARCHAR(1000)
);
```

##### `trading_platform` - Торговые площадки
```sql
CREATE TABLE trading_platform (
    id INTEGER PRIMARY KEY,
    trading_platform_name VARCHAR(255),
    trading_platform_url VARCHAR(500)
);
```

---

## Логика поиска торгов

### Типы торгов

#### 1. Новые торги (`tender_type = 'new'`)
- **Статус:** `status_id = 1`
- **Условие:** Торги, принимающие заявки
- **SQL фильтр:** `r.status_id = 1`

#### 2. Разыгранные торги (`tender_type = 'won'`)
- **Статус:** `status_id IN (2, 3)`
- **Условие:** Торги, где уже определен победитель
- **SQL фильтр:** `r.status_id IN (2, 3)`

#### 3. Работа комиссии (`tender_type = 'commission'`)
- **Статус:** `status_id = 2` (для 44-ФЗ)
- **Условие:** Торги на этапе работы комиссии
- **SQL фильтр:** `r.status_id = 2`

### Алгоритм фильтрации

#### Шаг 1: Получение OKPD кодов пользователя

```sql
-- Получаем ID ОКПД кодов из категорий пользователя
SELECT DISTINCT okpd_table.id
FROM okpd_from_users user_okpd
JOIN collection_codes_okpd okpd_table ON (
    okpd_table.main_code = user_okpd.okpd_code 
    OR okpd_table.sub_code = user_okpd.okpd_code
)
WHERE user_okpd.user_id = :user_id
    AND (user_okpd.category_id = :category_id OR :category_id IS NULL);
```

**Важно:** Если у пользователя нет OKPD кодов, возвращаем пустой список торгов.

#### Шаг 2: Получение стоп-слов пользователя

```sql
SELECT stop_word
FROM stop_words_names
WHERE user_id = :user_id;
```

#### Шаг 3: Построение SQL запроса

**Базовый запрос для новых торгов 44-ФЗ:**

```sql
SELECT DISTINCT 
    r.id,
    r.auction_name,
    r.start_date,
    r.end_date,
    r.status_id,
    c.customer_short_name,
    c.customer_full_name,
    reg.name as region_name,
    okpd.main_code as okpd_main_code,
    okpd.sub_code as okpd_sub_code,
    okpd.name as okpd_name,
    tdm.match_count,
    tdm.match_percentage,
    tdm.is_interesting,
    tdm.processed_at
FROM reestr_contract_44_fz r
LEFT JOIN customer c ON r.customer_id = c.id
LEFT JOIN region reg ON r.region_id = reg.id
LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
LEFT JOIN tender_document_matches tdm 
    ON tdm.tender_id = r.id AND tdm.registry_type = '44fz'
WHERE 1=1
    -- Фильтр по статусу (новые торги)
    AND r.status_id = 1
    -- Фильтр по OKPD кодам
    AND r.okpd_id IN (
        SELECT DISTINCT okpd_table.id
        FROM okpd_from_users user_okpd
        JOIN collection_codes_okpd okpd_table ON (
            okpd_table.main_code = user_okpd.okpd_code 
            OR okpd_table.sub_code = user_okpd.okpd_code
        )
        WHERE user_okpd.user_id = :user_id
    )
    -- Фильтр по стоп-словам (исключаем торги, содержащие фразы)
    AND NOT EXISTS (
        SELECT 1 FROM stop_words_names sw
        WHERE sw.user_id = :user_id
            AND LOWER(r.auction_name) LIKE '%' || LOWER(sw.stop_word) || '%'
    )
    -- Фильтр по региону (если указан)
    AND (:region_id IS NULL OR r.region_id = :region_id)
    -- Исключаем неинтересные торги
    AND NOT EXISTS (
        SELECT 1 FROM tender_document_matches tdm_filter
        WHERE tdm_filter.tender_id = r.id 
            AND tdm_filter.registry_type = '44fz'
            AND tdm_filter.is_interesting = FALSE
    )
ORDER BY tdm.processed_at DESC NULLS LAST, r.start_date DESC, r.id DESC
LIMIT :limit;
```

**Важные моменты:**

1. **Стоп-слова:** Проверка выполняется по **точным фразам** (не отдельным словам)
   - `LOWER(r.auction_name) LIKE '%системы вентиляции%'` ✅
   - НЕ `LOWER(r.auction_name) LIKE '%системы%'` ❌

2. **OKPD фильтрация:** Сопоставление по `main_code` ИЛИ `sub_code`

3. **Исключение неинтересных:** Торги с `is_interesting = FALSE` исключаются из поиска

4. **Регион:** Опциональный фильтр, если `region_id` не указан - все регионы

### Оптимизированный запрос с CTE

Для лучшей производительности используйте CTE:

```sql
WITH user_okpd_ids AS (
    SELECT DISTINCT okpd_table.id
    FROM okpd_from_users user_okpd
    JOIN collection_codes_okpd okpd_table ON (
        okpd_table.main_code = user_okpd.okpd_code 
        OR okpd_table.sub_code = user_okpd.okpd_code
    )
    WHERE user_okpd.user_id = :user_id
),
user_stop_words AS (
    SELECT LOWER(stop_word) as stop_word
    FROM stop_words_names
    WHERE user_id = :user_id
)
SELECT DISTINCT r.id, r.auction_name, ...
FROM reestr_contract_44_fz r
WHERE r.status_id = 1
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
LIMIT :limit;
```

---

## Логика анализа документации

### Общий процесс

```
1. Получение списка торгов
   ↓
2. Для каждого торга:
   ├─ 2.1. Проверка: уже обработан?
   ├─ 2.2. Получение списка документов
   ├─ 2.3. Выбор документов для скачивания
   ├─ 2.4. Скачивание документов
   ├─ 2.5. Распаковка архивов (RAR, ZIP, 7Z)
   ├─ 2.6. Подготовка Excel/Word/PDF файлов
   ├─ 2.7. Поиск совпадений с товарами
   ├─ 2.8. Сохранение результатов в БД
   └─ 2.9. Очистка временных файлов
```

### Детальное описание этапов

#### Этап 1: Проверка обработанных торгов

**Таблица:** `tender_document_matches`

```sql
-- Проверка, обработан ли торг
SELECT id, match_count, match_percentage, is_interesting, processed_at
FROM tender_document_matches
WHERE tender_id = :tender_id 
    AND registry_type = :registry_type;
```

**Если запись существует:**
- Пропускаем торг (уже обработан)
- Или переобрабатываем, если нужно

#### Этап 2: Получение документов торга

**Таблица:** `tender_documents` (структура зависит от вашей БД)

```sql
SELECT 
    id,
    file_name,
    file_url,
    file_type,          -- 'archive', 'excel', 'word', 'pdf'
    file_size,
    is_archive_part     -- true для частей архивов (part1.rar, part2.rar)
FROM tender_documents
WHERE tender_id = :tender_id
    AND registry_type = :registry_type
ORDER BY file_name;
```

#### Этап 3: Выбор документов для скачивания

**Критерии выбора:**

1. **Приоритет документов:**
   - Сметы (Excel файлы с названиями типа "Смета", "КП", "Спецификация")
   - Проектная документация (архивы с названиями типа "Проект", "Рабочая документация")
   - Исключаем: "Извещение", "Протокол", "Контракт" (не содержат спецификаций)

2. **Группировка архивов:**
   - Если есть `part1.rar`, `part2.rar` - скачиваем все части
   - После скачивания объединяем в один архив

3. **Формат файлов:**
   - Поддерживаемые: `.xlsx`, `.xls`, `.docx`, `.doc`, `.pdf`
   - Архивы: `.rar`, `.zip`, `.7z`

#### Этап 4: Скачивание документов

**Алгоритм:**

1. Создать папку: `{download_dir}/{registry_type}_{tender_id}_{tender_type}/`
2. Скачать файлы параллельно (рекомендуется 2-4 потока)
3. Проверить целостность файлов
4. Для архивов с частями - дождаться всех частей

**Пример структуры папки:**
```
44fz_514805_won/
├── Проектная документация.part1.rar
├── Проектная документация.part2.rar
├── Рабочая документация.rar
├── Смета.xlsx
└── extract_Проектная_документация_abc123/
    ├── Спецификация.xlsx
    ├── Ведомость объемов.xlsx
    └── ...
```

#### Этап 5: Распаковка архивов

**Алгоритм:**

1. Определить тип архива (RAR, ZIP, 7Z)
2. Создать папку для распаковки: `extract_{archive_name}_{uuid}/`
3. Распаковать архив
4. Найти все поддерживаемые файлы внутри:
   - Рекурсивный поиск: `*.xlsx`, `*.xls`, `*.docx`, `*.doc`, `*.pdf`
5. Добавить найденные файлы в очередь обработки

**Важно:**
- Части архивов (part1, part2) обрабатываются вместе
- Временные папки распаковки можно удалить после обработки

#### Этап 6: Подготовка файлов

**Для Excel файлов:**
1. Проверить, не поврежден ли файл
2. Если поврежден - удалить и попробовать скачать заново
3. Открыть файл и получить список листов
4. Подготовить пути к файлам для поиска

**Для Word/PDF:**
- Используются напрямую (без предобработки)

#### Этап 7: Поиск совпадений

**Источник данных:** Таблица `products` из БД `product_catalog`

```sql
-- Получение списка товаров для поиска
SELECT name
FROM products
WHERE name IS NOT NULL AND name != '';
```

**Алгоритм поиска:**

1. Для каждого файла (Excel/Word/PDF):
   - Открыть файл
   - Для Excel: обработать каждый лист, каждую ячейку
   - Для Word/PDF: извлечь текст

2. Для каждого товара из каталога:
   - Искать точное совпадение названия в тексте
   - Искать частичное совпадение (если настроено)
   - Рассчитать score совпадения (0-100%)

3. Сохранить найденные совпадения:
   - Название товара
   - Файл, лист, строка, ячейка
   - Score совпадения
   - Контекст (текст вокруг совпадения)

**Пример результата:**
```json
{
  "matches": [
    {
      "product_name": "Кирпич керамический",
      "file_path": "Смета.xlsx",
      "sheet_name": "Лист1",
      "row_number": 15,
      "cell_address": "B15",
      "match_score": 100.0,
      "context_text": "Кирпич керамический, марка М100, количество 5000 шт"
    }
  ]
}
```

#### Этап 8: Сохранение результатов

**Вставка в `tender_document_matches`:**

```sql
INSERT INTO tender_document_matches (
    tender_id,
    registry_type,
    folder_name,
    match_count,
    match_percentage,
    is_interesting,
    processed_at,
    processing_time_seconds,
    total_file_size_bytes
) VALUES (
    :tender_id,
    :registry_type,
    :folder_name,
    :match_count,
    :match_percentage,
    TRUE,  -- По умолчанию интересный
    CURRENT_TIMESTAMP,
    :processing_time,
    :total_size
)
ON CONFLICT (tender_id, registry_type) 
DO UPDATE SET
    match_count = EXCLUDED.match_count,
    match_percentage = EXCLUDED.match_percentage,
    processed_at = EXCLUDED.processed_at,
    processing_time_seconds = EXCLUDED.processing_time_seconds,
    total_file_size_bytes = EXCLUDED.total_file_size_bytes,
    updated_at = CURRENT_TIMESTAMP;
```

**Вставка деталей в `tender_document_match_details`:**

```sql
INSERT INTO tender_document_match_details (
    match_id,
    product_name,
    file_path,
    sheet_name,
    row_number,
    cell_address,
    match_score,
    context_text
) VALUES (
    :match_id,
    :product_name,
    :file_path,
    :sheet_name,
    :row_number,
    :cell_address,
    :match_score,
    :context_text
);
```

#### Этап 9: Очистка временных файлов

- Удалить папки распаковки (`extract_*`)
- Опционально: удалить скачанные файлы (если не нужны для повторного анализа)
- Сохранить только `folder_name` в БД для отслеживания

---

## SQL запросы

### Получение новых торгов с фильтрами

```sql
-- Параметры: :user_id, :region_id (опционально), :limit

WITH user_okpd_ids AS (
    SELECT DISTINCT okpd_table.id
    FROM okpd_from_users user_okpd
    JOIN collection_codes_okpd okpd_table ON (
        okpd_table.main_code = user_okpd.okpd_code 
        OR okpd_table.sub_code = user_okpd.okpd_code
    )
    WHERE user_okpd.user_id = :user_id
),
user_stop_words AS (
    SELECT LOWER(stop_word) as stop_word
    FROM stop_words_names
    WHERE user_id = :user_id
)
SELECT DISTINCT 
    r.id,
    r.auction_name,
    r.start_date,
    r.end_date,
    r.status_id,
    c.customer_short_name,
    reg.name as region_name,
    okpd.main_code as okpd_main_code,
    okpd.name as okpd_name,
    tdm.match_count,
    tdm.match_percentage,
    tdm.is_interesting,
    tdm.processed_at
FROM reestr_contract_44_fz r
LEFT JOIN customer c ON r.customer_id = c.id
LEFT JOIN region reg ON r.region_id = reg.id
LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
LEFT JOIN tender_document_matches tdm 
    ON tdm.tender_id = r.id AND tdm.registry_type = '44fz'
WHERE r.status_id = 1  -- Новые торги
    AND r.okpd_id IN (SELECT id FROM user_okpd_ids)
    AND NOT EXISTS (
        SELECT 1 FROM user_stop_words sw
        WHERE LOWER(r.auction_name) LIKE '%' || sw.stop_word || '%'
    )
    AND (:region_id IS NULL OR r.region_id = :region_id)
    AND NOT EXISTS (
        SELECT 1 FROM tender_document_matches tdm_filter
        WHERE tdm_filter.tender_id = r.id 
            AND tdm_filter.registry_type = '44fz'
            AND tdm_filter.is_interesting = FALSE
    )
ORDER BY tdm.processed_at DESC NULLS LAST, r.start_date DESC
LIMIT :limit;
```

### Получение разыгранных торгов

```sql
-- Аналогично, но с фильтром: r.status_id IN (2, 3)
WHERE r.status_id IN (2, 3)  -- Разыгранные торги
```

### Подсчет торгов (для пагинации)

```sql
WITH user_okpd_ids AS (
    SELECT DISTINCT okpd_table.id
    FROM okpd_from_users user_okpd
    JOIN collection_codes_okpd okpd_table ON (
        okpd_table.main_code = user_okpd.okpd_code 
        OR okpd_table.sub_code = user_okpd.okpd_code
    )
    WHERE user_okpd.user_id = :user_id
),
user_stop_words AS (
    SELECT LOWER(stop_word) as stop_word
    FROM stop_words_names
    WHERE user_id = :user_id
)
SELECT COUNT(DISTINCT r.id) as total_count
FROM reestr_contract_44_fz r
WHERE r.status_id = 1
    AND r.okpd_id IN (SELECT id FROM user_okpd_ids)
    AND NOT EXISTS (
        SELECT 1 FROM user_stop_words sw
        WHERE LOWER(r.auction_name) LIKE '%' || sw.stop_word || '%'
    )
    AND (:region_id IS NULL OR r.region_id = :region_id)
    AND NOT EXISTS (
        SELECT 1 FROM tender_document_matches tdm_filter
        WHERE tdm_filter.tender_id = r.id 
            AND tdm_filter.registry_type = '44fz'
            AND tdm_filter.is_interesting = FALSE
    );
```

### Получение деталей совпадений

```sql
SELECT 
    tdm.id as match_id,
    tdm.tender_id,
    tdm.registry_type,
    tdm.match_count,
    tdm.match_percentage,
    tdd.product_name,
    tdd.file_path,
    tdd.sheet_name,
    tdd.row_number,
    tdd.cell_address,
    tdd.match_score,
    tdd.context_text
FROM tender_document_matches tdm
LEFT JOIN tender_document_match_details tdd ON tdd.match_id = tdm.id
WHERE tdm.tender_id = :tender_id
    AND tdm.registry_type = :registry_type
ORDER BY tdd.match_score DESC, tdd.row_number;
```

---

## API эндпоинты (рекомендации)

### 1. Поиск торгов

```
GET /api/tenders
Query parameters:
  - user_id (required)
  - registry_type: '44fz' | '223fz' | 'both'
  - tender_type: 'new' | 'won' | 'commission'
  - region_id (optional)
  - category_id (optional) - фильтр по категории OKPD
  - limit (default: 100)
  - offset (default: 0)

Response:
{
  "total": 150,
  "tenders": [
    {
      "id": 12345,
      "auction_name": "Поставка строительных материалов",
      "start_date": "2024-01-15",
      "end_date": "2024-02-15",
      "status_id": 1,
      "customer": {
        "short_name": "ООО Заказчик",
        "full_name": "Общество с ограниченной ответственностью..."
      },
      "region": {
        "name": "Московская область",
        "code": "50"
      },
      "okpd": {
        "main_code": "41.20.10.000",
        "name": "Кирпич строительный"
      },
      "analysis": {
        "match_count": 25,
        "match_percentage": 85.5,
        "is_interesting": true,
        "processed_at": "2024-01-14T10:30:00Z"
      }
    }
  ]
}
```

### 2. Получение деталей анализа

```
GET /api/tenders/:tender_id/analysis
Query parameters:
  - registry_type: '44fz' | '223fz'

Response:
{
  "tender_id": 12345,
  "registry_type": "44fz",
  "match_count": 25,
  "match_percentage": 85.5,
  "is_interesting": true,
  "processed_at": "2024-01-14T10:30:00Z",
  "details": [
    {
      "product_name": "Кирпич керамический",
      "file_path": "Смета.xlsx",
      "sheet_name": "Лист1",
      "row_number": 15,
      "cell_address": "B15",
      "match_score": 100.0,
      "context_text": "Кирпич керамический, марка М100..."
    }
  ]
}
```

### 3. Запуск анализа документации

```
POST /api/tenders/analyze
Body:
{
  "tender_ids": [12345, 12346],  // или null для всех
  "registry_type": "44fz",
  "tender_type": "new",
  "user_id": 1
}

Response:
{
  "job_id": "abc123",
  "status": "started",
  "message": "Анализ запущен для 2 торгов"
}
```

### 4. Статус анализа

```
GET /api/tenders/analyze/:job_id

Response:
{
  "job_id": "abc123",
  "status": "processing",  // started | processing | completed | failed
  "progress": {
    "total": 100,
    "processed": 45,
    "errors": 2
  },
  "results": [
    {
      "tender_id": 12345,
      "status": "completed",
      "match_count": 25
    }
  ]
}
```

### 5. Управление настройками

```
GET /api/settings/okpd?user_id=1
POST /api/settings/okpd
DELETE /api/settings/okpd/:id

GET /api/settings/stop-words?user_id=1
POST /api/settings/stop-words
DELETE /api/settings/stop-words/:id

GET /api/settings/categories?user_id=1
POST /api/settings/categories
```

---

## Важные замечания

### Безопасность

1. **OKPD коды обязательны:** Если у пользователя нет OKPD кодов, возвращайте пустой список (не все торги!)
2. **Валидация входных данных:** Проверяйте `user_id`, `registry_type`, `tender_type`
3. **SQL инъекции:** Используйте параметризованные запросы
4. **Права доступа:** Проверяйте, что пользователь имеет доступ к своим настройкам

### Производительность

1. **Индексы:** Убедитесь, что есть индексы на:
   - `reestr_contract_44_fz.status_id`
   - `reestr_contract_44_fz.okpd_id`
   - `okpd_from_users.user_id`
   - `stop_words_names.user_id`
   - `tender_document_matches(tender_id, registry_type)`

2. **Кэширование:** Кэшируйте результаты поиска торгов (TTL: 30 дней, проверка статусов раз в день)

3. **Параллельная обработка:** Анализ документации можно запускать параллельно на разных машинах (используйте `folder_name` для синхронизации)

### Обработка ошибок

1. **Пустой OKPD:** Возвращайте ошибку, а не все торги
2. **Поврежденные файлы:** Удаляйте и пытайтесь скачать заново (максимум 1 попытка)
3. **Таймауты:** Устанавливайте таймауты для скачивания файлов (рекомендуется 60 секунд)

---

## Контакты и поддержка

При возникновении вопросов обращайтесь к разработчику системы.

**Версия документа:** 1.0  
**Дата обновления:** 2024-01-14

