"""
MODULE: scripts.migrate_folder_names_to_db
RESPONSIBILITY: Migrating processed folder names to the database.
ALLOWED: sys, re, pathlib, typing, config.settings, core.tender_database, loguru.
FORBIDDEN: None.
ERRORS: None.

Скрипт для переноса названий обработанных папок в БД.

Находит все папки с торгов (44fz_*, 223fz_*) и обновляет записи в tender_document_matches,
добавляя folder_name для уже обработанных торгов.
"""

import sys
import re
from pathlib import Path
from typing import List, Dict, Optional

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import config
from core.tender_database import TenderDatabaseManager
from loguru import logger

# Паттерн для определения папок торгов
FOLDER_PATTERN = re.compile(r"^(?P<registry>44fz|223fz)_(?P<tender_id>\d+)(?:_won)?$", re.IGNORECASE)


def find_processed_folders(download_dir: Path) -> List[Dict[str, str]]:
    """
    Находит все папки с торгов в директории загрузки.
    
    Args:
        download_dir: Директория с папками торгов
        
    Returns:
        Список словарей с информацией о папках: {tender_id, registry_type, folder_name}
    """
    folders = []
    if not download_dir.exists():
        logger.warning(f"Директория {download_dir} не существует")
        return folders
    
    for entry in download_dir.iterdir():
        if not entry.is_dir():
            continue
        
        match = FOLDER_PATTERN.match(entry.name)
        if not match:
            continue
        
        tender_id = int(match.group("tender_id"))
        registry_type = match.group("registry").lower()
        folder_name = entry.name
        
        folders.append({
            "tender_id": tender_id,
            "registry_type": registry_type,
            "folder_name": folder_name,
        })
    
    logger.info(f"Найдено папок торгов: {len(folders)}")
    return folders


def update_folder_names_in_db(
    db_manager: TenderDatabaseManager,
    folders: List[Dict[str, str]],
) -> Dict[str, int]:
    """
    Обновляет записи в БД, добавляя folder_name для уже обработанных торгов.
    
    Args:
        db_manager: Менеджер БД
        folders: Список папок с информацией о торгах
        
    Returns:
        Словарь со статистикой: {updated, skipped, errors}
    """
    stats = {"updated": 0, "skipped": 0, "errors": 0}
    
    # Проверяем, существует ли поле folder_name
    check_column_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'tender_document_matches' 
            AND column_name = 'folder_name'
        )
    """
    try:
        result = db_manager.execute_query(check_column_query)
        has_folder_name = result[0].get('exists', False) if result else False
        
        if not has_folder_name:
            logger.error("Поле folder_name не существует в таблице tender_document_matches!")
            logger.error("Сначала выполните миграцию: scripts/add_folder_name_to_tender_document_matches.sql")
            return stats
    except Exception as e:
        logger.error(f"Ошибка при проверке существования поля folder_name: {e}")
        return stats
    
    # Обновляем записи батчами
    batch_size = 100
    for i in range(0, len(folders), batch_size):
        batch = folders[i:i + batch_size]
        
        for folder_info in batch:
            tender_id = folder_info["tender_id"]
            registry_type = folder_info["registry_type"]
            folder_name = folder_info["folder_name"]
            
            try:
                # Проверяем, существует ли запись для этого торга
                check_query = """
                    SELECT id FROM tender_document_matches
                    WHERE tender_id = %s AND registry_type = %s
                """
                existing = db_manager.execute_query(check_query, (tender_id, registry_type))
                
                if existing:
                    # Обновляем folder_name, если он еще не установлен
                    update_query = """
                        UPDATE tender_document_matches
                        SET folder_name = %s
                        WHERE tender_id = %s AND registry_type = %s
                        AND (folder_name IS NULL OR folder_name = '')
                    """
                    db_manager.execute_update(update_query, (folder_name, tender_id, registry_type))
                    stats["updated"] += 1
                    logger.debug(f"Обновлен folder_name для торга {tender_id} ({registry_type}): {folder_name}")
                else:
                    stats["skipped"] += 1
                    logger.debug(f"Пропущен торг {tender_id} ({registry_type}): запись в БД не найдена")
                    
            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Ошибка при обновлении торга {tender_id} ({registry_type}): {e}")
    
    return stats


def main():
    """Основная функция."""
    logger.info("=" * 80)
    logger.info("Миграция названий папок в БД")
    logger.info("=" * 80)
    
    # Подключаемся к БД
    try:
        tender_db = TenderDatabaseManager(config.tender_database)
        tender_db.connect()
        logger.info("✅ Подключение к БД установлено")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        sys.exit(1)
    
    # Определяем директорию загрузки
    if config.document_download_dir:
        download_dir = Path(config.document_download_dir).expanduser().resolve()
    else:
        default_dir = Path.home() / "Downloads" / "ЕИС_Документация"
        download_dir = default_dir
        logger.warning(f"DOCUMENT_DOWNLOAD_DIR не настроен, используем: {download_dir}")
    
    logger.info(f"📁 Директория загрузки: {download_dir}")
    
    # Находим все папки торгов
    logger.info("🔍 Поиск папок торгов...")
    folders = find_processed_folders(download_dir)
    
    if not folders:
        logger.warning("Не найдено папок торгов для миграции")
        tender_db.disconnect()
        return
    
    logger.info(f"📊 Найдено папок: {len(folders)}")
    
    # Обновляем записи в БД
    logger.info("💾 Обновление записей в БД...")
    stats = update_folder_names_in_db(tender_db, folders)
    
    # Выводим статистику
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 ИТОГИ МИГРАЦИИ")
    logger.info("=" * 80)
    logger.info(f"✅ Обновлено записей: {stats['updated']}")
    logger.info(f"⏭️  Пропущено (нет записи в БД): {stats['skipped']}")
    logger.info(f"❌ Ошибок: {stats['errors']}")
    logger.info("")
    
    # Закрываем соединение
    tender_db.disconnect()
    logger.info("✅ Готово!")


if __name__ == "__main__":
    main()

