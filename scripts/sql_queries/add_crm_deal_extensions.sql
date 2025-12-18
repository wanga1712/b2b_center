-- Миграция: расширение CRM-модели для сделок в воронке продаж (контакты, роли, товары КП)
-- База: tender_monitor
-- ВАЖНО: таблицы customer и contractor уже существуют и не изменяются.

BEGIN;

-- 1. Роли для заказчиков
CREATE TABLE IF NOT EXISTS customer_role (
    id          bigserial PRIMARY KEY,
    customer_id bigint NOT NULL REFERENCES customer(id),
    role        text NOT NULL CHECK (role IN ('customer')),
    created_at  timestamptz DEFAULT now()
);

-- Уникальность роли на заказчика
CREATE UNIQUE INDEX IF NOT EXISTS ux_customer_role_customer_id_role
    ON customer_role (customer_id, role);

-- Инициализация: всем существующим заказчикам выдаём роль "customer"
INSERT INTO customer_role (customer_id, role)
SELECT c.id, 'customer'
FROM customer c
LEFT JOIN customer_role cr ON cr.customer_id = c.id AND cr.role = 'customer'
WHERE cr.id IS NULL;


-- 2. Роли для подрядчиков / проектировщиков / поставщиков
CREATE TABLE IF NOT EXISTS contractor_role (
    id            bigserial PRIMARY KEY,
    contractor_id bigint NOT NULL REFERENCES contractor(id),
    role          text NOT NULL CHECK (role IN ('contractor','designer','supplier')),
    is_primary    boolean NOT NULL DEFAULT true,
    created_at    timestamptz DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_contractor_role_contractor_id_role
    ON contractor_role (contractor_id, role);

-- Инициализация: всем существующим подрядчикам ставим роль "contractor"
INSERT INTO contractor_role (contractor_id, role, is_primary)
SELECT c.id, 'contractor', true
FROM contractor c
LEFT JOIN contractor_role cr ON cr.contractor_id = c.id AND cr.role = 'contractor'
WHERE cr.id IS NULL;


-- 3. Контакты
CREATE TABLE IF NOT EXISTS contact (
    id           bigserial PRIMARY KEY,
    full_name    text NOT NULL,
    department   text,
    position     text,
    birth_date   date,
    phone_mobile text,
    email        text,
    notes        text,
    created_at   timestamptz DEFAULT now(),
    updated_at   timestamptz DEFAULT now()
);


-- 4. Гибкие связи контактов с компаниями и сделками
-- ВАЖНО: deal_id ссылается на sales_deals.id (текущая таблица сделок воронок)
CREATE TABLE IF NOT EXISTS contact_link (
    id            bigserial PRIMARY KEY,
    contact_id    bigint NOT NULL REFERENCES contact(id),
    customer_id   bigint REFERENCES customer(id),
    contractor_id bigint REFERENCES contractor(id),
    deal_id       bigint REFERENCES sales_deals(id),
    role          text,
    is_primary    boolean DEFAULT false,
    created_at    timestamptz DEFAULT now()
);

-- Ограничение: хотя бы одно из customer_id / contractor_id / deal_id не NULL
ALTER TABLE contact_link
    ADD CONSTRAINT contact_link_target_not_null
    CHECK (
        customer_id IS NOT NULL
        OR contractor_id IS NOT NULL
        OR deal_id IS NOT NULL
    );

CREATE INDEX IF NOT EXISTS idx_contact_link_contact_id ON contact_link(contact_id);
CREATE INDEX IF NOT EXISTS idx_contact_link_customer_id ON contact_link(customer_id);
CREATE INDEX IF NOT EXISTS idx_contact_link_contractor_id ON contact_link(contractor_id);
CREATE INDEX IF NOT EXISTS idx_contact_link_deal_id ON contact_link(deal_id);


-- 5. Позиции КП / товаров внутри сделки
-- Привязка к существующей таблице sales_deals
CREATE TABLE IF NOT EXISTS deal_item (
    id             bigserial PRIMARY KEY,
    deal_id        bigint NOT NULL REFERENCES sales_deals(id),
    product_name   text NOT NULL,
    product_code   text,
    is_analog      boolean NOT NULL DEFAULT false,
    unit           text NOT NULL,
    quantity       numeric(18,3) NOT NULL,
    price_per_unit numeric(18,2) NOT NULL,
    total_price    numeric(18,2) GENERATED ALWAYS AS (quantity * price_per_unit) STORED,
    comment        text,
    created_at     timestamptz DEFAULT now(),
    updated_at     timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_deal_item_deal_id ON deal_item(deal_id);


COMMIT;


