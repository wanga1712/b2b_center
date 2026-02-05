import sys
sys.path.insert(0, '.')

from config.settings import Config
from core.tender_database import TenderDatabaseManager
from loguru import logger

config = Config()
db_manager = TenderDatabaseManager(config.tender_database)
db_manager.connect()

logger.info('=== ТЕСТИРОВАНИЕ ПОЛНОГО ЗАПРОСА ===')

try:
    # Полный запрос как в WonTendersService
    query = """
SELECT DISTINCT
    r.id,
    r.contract_number,
    r.tender_link,
    r.start_date,
    r.end_date,
    r.delivery_start_date,
    r.delivery_end_date,
    r.auction_name,
    r.initial_price,
    r.final_price,
    r.guarantee_amount,
    r.customer_id,
    r.contractor_id,
    r.trading_platform_id,
    r.okpd_id,
    r.region_id,
    r.delivery_region,
    r.delivery_address,
    r.status_id,
    c.customer_short_name,
    c.customer_full_name,
    reg.name as region_name,
    reg.code as region_code,
    cont.short_name as contractor_short_name,
    cont.full_name as contractor_full_name,
    okpd.main_code as okpd_main_code,
    okpd.sub_code as okpd_sub_code,
    okpd.name as okpd_name,
    tp.trading_platform_name as platform_name,
    tp.trading_platform_url as platform_url,
    c.customer_short_name as balance_holder_name,
    c.customer_inn as balance_holder_inn,
    tdm.processed_at

    FROM reestr_contract_44_fz r
    LEFT JOIN customer c ON r.customer_id = c.id
    LEFT JOIN region reg ON r.region_id = reg.id
    LEFT JOIN contractor cont ON r.contractor_id = cont.id
    LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
    LEFT JOIN trading_platform tp ON r.trading_platform_id = tp.id
    LEFT JOIN tender_document_matches tdm ON tdm.tender_id = r.id AND tdm.registry_type = '44fz'
 WHERE 1=1 AND r.status_id IN (2, 3)
 LIMIT 5
"""

    logger.info('Выполняем запрос...')
    result = db_manager.execute_query(query)

    logger.info(f'Получено результатов: {len(result) if result else 0}')

    if result:
        for i, row in enumerate(result):
            logger.info(f'{i+1}. ID: {row["id"]}, Status: {row["status_id"]}, Name: {row["auction_name"][:50]}...')
    else:
        logger.warning('Запрос вернул пустой результат!')

except Exception as e:
    logger.error(f'Ошибка: {e}')
    import traceback
    logger.error(traceback.format_exc())

db_manager.disconnect()
