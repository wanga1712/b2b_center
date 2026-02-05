import sys
sys.path.insert(0, '.')

from config.settings import Config
from core.tender_database import TenderDatabaseManager
from services.archive_runner.processed_tenders_repository import ProcessedTendersRepository
from scripts.cleanup_processed_folders import find_tender_folder, get_download_dirs
from loguru import logger

config = Config()
db_manager = TenderDatabaseManager(config.tender_database)
db_manager.connect()

try:
    # Проверим одну запись из tender_document_matches
    query = """
        SELECT tender_id, registry_type, folder_name
        FROM tender_document_matches
        WHERE folder_name IS NOT NULL
        LIMIT 1
    """

    result = db_manager.execute_query(query)
    if result:
        row = result[0]
        tender_id = row['tender_id']
        registry_type = row['registry_type']
        folder_name = row['folder_name']

        logger.info(f"Проверяем торг: {tender_id}, {registry_type}, папка: {folder_name}")

        download_dirs = get_download_dirs()
        logger.info(f"Директории поиска: {download_dirs}")

        found_path = find_tender_folder(download_dirs, registry_type, tender_id, folder_name)
        if found_path:
            logger.info(f"✅ Папка найдена: {found_path}")
        else:
            logger.info("❌ Папка не найдена")

    # Проверим сколько всего записей с folder_name
    count_query = "SELECT COUNT(*) as cnt FROM tender_document_matches WHERE folder_name IS NOT NULL"
    count_result = db_manager.execute_query(count_query)
    if count_result:
        logger.info(f"Всего записей с folder_name: {count_result[0]['cnt']}")

except Exception as e:
    logger.error(f"Ошибка: {e}")

db_manager.disconnect()
