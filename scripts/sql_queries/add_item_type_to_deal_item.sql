-- Миграция: добавление поля item_type в таблицу deal_item
-- Дата: 2025-12-18
-- Описание: Добавляет поле item_type для различения типов позиций (материал, работа, товар_кп)

-- Добавляем поле item_type (если еще не существует)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'deal_item' AND column_name = 'item_type'
    ) THEN
        ALTER TABLE deal_item ADD COLUMN item_type VARCHAR(20) DEFAULT 'товар_кп';
    END IF;
END $$;

-- Добавляем constraint для валидации значений (если еще не существует)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.constraint_column_usage 
        WHERE constraint_name = 'chk_item_type'
    ) THEN
        ALTER TABLE deal_item ADD CONSTRAINT chk_item_type 
        CHECK (item_type IN ('материал', 'работа', 'товар_кп'));
    END IF;
END $$;

-- Создаем индекс для быстрого поиска по типу
CREATE INDEX IF NOT EXISTS idx_deal_item_type ON deal_item(item_type);

-- Создаем индекс для поиска по сделке и типу
CREATE INDEX IF NOT EXISTS idx_deal_item_deal_type ON deal_item(deal_id, item_type);

-- Комментарии к полям
COMMENT ON COLUMN deal_item.item_type IS 'Тип позиции: материал (из проектной документации), работа (из проектной документации), товар_кп (для формирования КП из БД)';

