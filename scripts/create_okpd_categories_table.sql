-- Создание таблицы для категорий ОКПД
-- Позволяет группировать ОКПД коды по категориям (компьютеры, стройка, проекты и т.д.)

CREATE TABLE IF NOT EXISTS okpd_categories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Уникальность: один пользователь не может иметь две категории с одинаковым именем
    CONSTRAINT unique_user_category_name UNIQUE (user_id, name)
);

-- Добавление поля category_id в таблицу okpd_from_users
-- Если category_id NULL, то ОКПД код не привязан к категории
ALTER TABLE okpd_from_users 
ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES okpd_categories(id) ON DELETE SET NULL;

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_okpd_categories_user_id ON okpd_categories(user_id);
CREATE INDEX IF NOT EXISTS idx_okpd_from_users_category_id ON okpd_from_users(category_id);

-- Комментарии к таблице и полям
COMMENT ON TABLE okpd_categories IS 'Категории для группировки ОКПД кодов пользователя';
COMMENT ON COLUMN okpd_categories.user_id IS 'ID пользователя, которому принадлежит категория';
COMMENT ON COLUMN okpd_categories.name IS 'Название категории (например: компьютеры, стройка, проекты)';
COMMENT ON COLUMN okpd_categories.description IS 'Описание категории';
COMMENT ON COLUMN okpd_from_users.category_id IS 'ID категории, к которой привязан ОКПД код (NULL = не привязан)';

