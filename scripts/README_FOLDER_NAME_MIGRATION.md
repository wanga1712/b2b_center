# Миграция folder_name в БД

## Проблема
Код использует поле `folder_name` в таблице `tender_document_matches`, но это поле еще не создано в БД.

## Решение

### Шаг 1: Применить миграцию БД

Выполните SQL скрипт для создания поля `folder_name`:

```bash
# Через psql
psql -h localhost -U your_user -d tender_monitor -f scripts/add_folder_name_to_tender_document_matches.sql

# Или через любой SQL клиент (pgAdmin, DBeaver и т.д.)
# Откройте файл scripts/add_folder_name_to_tender_document_matches.sql и выполните его
```

### Шаг 2: Перенести данные из папок в БД

После применения миграции запустите скрипт для переноса названий уже обработанных папок:

```bash
python scripts/migrate_folder_names_to_db.py
```

Скрипт:
- Найдет все папки торгов в директории загрузки (44fz_*, 223fz_*)
- Обновит записи в БД, добавив `folder_name` для уже обработанных торгов
- Покажет статистику: сколько записей обновлено, пропущено, ошибок

### Шаг 3: Проверить результат

После выполнения скрипта проверьте, что данные перенесены:

```sql
SELECT tender_id, registry_type, folder_name, processed_at 
FROM tender_document_matches 
WHERE folder_name IS NOT NULL 
ORDER BY processed_at DESC 
LIMIT 10;
```

## Важно

- **Сначала** примените миграцию (Шаг 1)
- **Затем** запустите скрипт переноса данных (Шаг 2)
- Код теперь работает безопасно: если поле `folder_name` не существует, он не будет падать, но и не будет использовать это поле

