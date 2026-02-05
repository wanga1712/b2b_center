-- Создание таблицы для хранения пользовательских фраз для поиска по документации

CREATE TABLE IF NOT EXISTS user_search_phrases (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    phrase TEXT NOT NULL,
    setting_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, phrase)
);

-- Индекс для быстрого поиска по user_id
CREATE INDEX IF NOT EXISTS idx_user_search_phrases_user_id ON user_search_phrases(user_id);

-- Комментарии
COMMENT ON TABLE user_search_phrases IS 'Пользовательские фразы для поиска по документации торгов (например, "инъектирование", "усиление")';
COMMENT ON COLUMN user_search_phrases.user_id IS 'ID пользователя';
COMMENT ON COLUMN user_search_phrases.phrase IS 'Фраза для поиска';
COMMENT ON COLUMN user_search_phrases.setting_id IS 'ID настройки (опционально)';

