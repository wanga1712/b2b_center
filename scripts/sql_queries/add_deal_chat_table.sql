-- Миграция: таблица для чата по сделкам (deal_chat)
-- База: tender_monitor
-- Назначение: хранение сообщений между сотрудниками и AI-агентом в рамках сделки

BEGIN;

-- Таблица сообщений чата по сделкам
CREATE TABLE IF NOT EXISTS deal_chat (
    id BIGSERIAL PRIMARY KEY,
    deal_id BIGINT NOT NULL REFERENCES sales_deals(id) ON DELETE CASCADE,
    sender_id BIGINT, -- user_id отправителя (NULL для AI-агента)
    sender_type TEXT NOT NULL CHECK (sender_type IN ('user', 'ai_agent')),
    message_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_read BOOLEAN DEFAULT FALSE,
    metadata JSONB -- Дополнительные данные (например, тип AI-агента, контекст)
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_deal_chat_deal_id ON deal_chat(deal_id);
CREATE INDEX IF NOT EXISTS idx_deal_chat_created_at ON deal_chat(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deal_chat_sender_id ON deal_chat(sender_id) WHERE sender_id IS NOT NULL;

-- Комментарии к таблице и полям
COMMENT ON TABLE deal_chat IS 'Сообщения чата по сделкам воронки продаж';
COMMENT ON COLUMN deal_chat.deal_id IS 'ID сделки (FK к sales_deals)';
COMMENT ON COLUMN deal_chat.sender_id IS 'ID пользователя-отправителя (NULL для AI-агента)';
COMMENT ON COLUMN deal_chat.sender_type IS 'Тип отправителя: user (сотрудник) или ai_agent (AI-ассистент)';
COMMENT ON COLUMN deal_chat.message_text IS 'Текст сообщения';
COMMENT ON COLUMN deal_chat.is_read IS 'Прочитано ли сообщение получателем';
COMMENT ON COLUMN deal_chat.metadata IS 'Дополнительные данные (JSONB): тип AI-агента, контекст, attachments и т.д.';

COMMIT;

