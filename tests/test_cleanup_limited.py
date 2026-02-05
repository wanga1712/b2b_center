import sys
sys.path.insert(0, '.')

from config.settings import Config
from core.tender_database import TenderDatabaseManager
from scripts.cleanup_processed_folders import get_download_dirs, find_tender_folder
from loguru import logger

config = Config()
db_manager = TenderDatabaseManager(config.tender_database)
db_manager.connect()

try:
    # Получаем только 10 записей для тестирования
    query = '''
    SELECT tender_id, registry_type, folder_name, processed_at
    FROM tender_document_matches
    WHERE folder_name IS NOT NULL
    ORDER BY processed_at DESC
    LIMIT 10
    '''

    results = db_manager.execute_query(query)
    logger.info(f'Тестируем на {len(results)} записях')

    download_dirs = get_download_dirs()
    found_count = 0

    for row in results:
        tender_id = row['tender_id']
        registry_type = row['registry_type']
        folder_name = row['folder_name']

        folder_path = find_tender_folder(download_dirs, registry_type, tender_id, folder_name)
        if folder_path:
            found_count += 1
            logger.info(f'✅ Найдена папка для торга {tender_id}: {folder_path.name}')
        else:
            logger.debug(f'❌ Папка для торга {tender_id} не найдена: {folder_name}')

    logger.info(f'Результат: найдено {found_count} папок из {len(results)}')

finally:
    db_manager.disconnect()
