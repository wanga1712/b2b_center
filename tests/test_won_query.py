import sys
sys.path.insert(0, '.')

# Импортируем только то, что нужно для построения запроса
from services.tender_repositories.tender_query_builder import TenderQueryBuilder
from services.tender_repositories.feeds.feed_filters import WonFilters
from datetime import date
from loguru import logger

logger.info('=== ТЕСТИРОВАНИЕ ПОСТРОЕНИЯ ЗАПРОСА ===')

try:
    # Создадим фильтры
    filters = WonFilters(
        user_id=1,
        okpd_codes=[],  # Пустой список
        stop_words=[],  # Пустой список
        region_id=None,
        category_id=None,
        limit=5,
        min_delivery_days=90
    )

    logger.info(f'Фильтры: okpd_codes={filters.okpd_codes}, stop_words={filters.stop_words}')

    # Построим запрос как в WonTendersService._build_won_query
    select_fields = TenderQueryBuilder.build_base_select_fields()
    table_name = TenderQueryBuilder.resolve_registry_table('44fz')
    base_joins = TenderQueryBuilder.build_base_joins(table_name, '44fz')
    query = f'SELECT DISTINCT {select_fields} {base_joins} WHERE 1=1'
    params = []

    logger.info(f'Базовый запрос: {query}')

    # Добавим фильтр разыгранных торгов
    won_filter, won_params = TenderQueryBuilder.build_won_tenders_filter(date.today(), use_status=True)
    query += won_filter
    params.extend(won_params)
    logger.info(f'После добавления won_filter: {query}')
    logger.info(f'Параметры: {params}')

    # Проверим результат фильтра
    logger.info(f'build_won_tenders_filter вернул: filter="{won_filter}", params={won_params}')

except Exception as e:
    logger.error(f'Ошибка: {e}')
    import traceback
    logger.error(traceback.format_exc())
