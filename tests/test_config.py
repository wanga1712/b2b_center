import sys
sys.path.insert(0, '.')

from config.settings import Config
from loguru import logger

config = Config()
logger.info(f'config.tender_database type: {type(config.tender_database)}')
logger.info(f'has execute_query: {hasattr(config.tender_database, "execute_query")}')

# Попробуем создать TenderDatabaseManager
from core.tender_database import TenderDatabaseManager
try:
    db_manager = TenderDatabaseManager(config.tender_database)
    logger.info(f'TenderDatabaseManager created successfully')
    logger.info(f'db_manager type: {type(db_manager)}')
    logger.info(f'db_manager has execute_query: {hasattr(db_manager, "execute_query")}')
except Exception as e:
    logger.error(f'Error creating TenderDatabaseManager: {e}')
