"""
Репозиторий для работы со сделками в воронках продаж
"""

from typing import List, Optional, Any, Dict
from datetime import date, datetime
from loguru import logger
from core.tender_database import TenderDatabaseManager
from psycopg2.extras import RealDictCursor
import json
from modules.crm.sales_funnel.models import PipelineType, Deal, DealStatus


class DealRepository:
    """Репозиторий для работы со сделками"""
    
    def __init__(self, db_manager: TenderDatabaseManager):
        self.db_manager = db_manager
    
    @staticmethod
    def _json_serializer(obj: Any) -> str:
        """Сериализатор для JSON, обрабатывающий даты и datetime"""
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    @staticmethod
    def _parse_metadata(metadata_value: Any) -> Optional[Dict[str, Any]]:
        """Парсинг metadata из БД (может быть строкой JSON или уже словарем)"""
        if not metadata_value:
            return None
        if isinstance(metadata_value, dict):
            return metadata_value
        if isinstance(metadata_value, str):
            try:
                return json.loads(metadata_value)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Не удалось распарсить metadata как JSON: {metadata_value}")
                return None
        return None
    
    def create_deal(self, deal: Deal) -> Optional[int]:
        """Создание новой сделки"""
        try:
            logger.info(
                f"Создание сделки: pipeline_type={deal.pipeline_type.value}, "
                f"user_id={deal.user_id}, tender_id={deal.tender_id}, stage_id={deal.stage_id}"
            )
            # Проверяем существование таблицы
            try:
                check_query = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'sales_deals'
                    )
                """
                table_exists = self.db_manager.execute_query(check_query)
                if not table_exists or not table_exists[0].get('exists', False):
                    logger.error("Таблица sales_deals не существует в базе данных tender_monitor")
                    logger.error("Попробуйте перезапустить приложение для автоматического создания таблиц")
                    return None
            except Exception as check_error:
                logger.error(f"Ошибка при проверке существования таблицы sales_deals: {check_error}", exc_info=True)
                return None
            
            # Проверяем на дубликаты: сделка с таким же tender_id, pipeline_type и user_id уже существует
            if deal.tender_id:
                duplicate_check_query = """
                    SELECT id FROM sales_deals
                    WHERE tender_id = %s AND pipeline_type = %s AND user_id = %s
                    LIMIT 1
                """
                existing = self.db_manager.execute_query(
                    duplicate_check_query,
                    (deal.tender_id, deal.pipeline_type.value, deal.user_id),
                    RealDictCursor
                )
                if existing and len(existing) > 0:
                    existing_id = existing[0]['id']
                    logger.warning(
                        f"Сделка с tender_id={deal.tender_id}, pipeline_type={deal.pipeline_type.value}, "
                        f"user_id={deal.user_id} уже существует (ID={existing_id}). Возвращаем существующий ID."
                    )
                    return existing_id
            
            query = """
                INSERT INTO sales_deals (
                    pipeline_type, stage_id, tender_id, name, description,
                    amount, margin, status, tender_status_id, user_id, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            # Сериализуем metadata с обработкой дат
            metadata_json = None
            if deal.metadata:
                try:
                    metadata_json = json.dumps(deal.metadata, default=self._json_serializer)
                except Exception as e:
                    logger.warning(f"Ошибка при сериализации metadata, сохраняем без original_data: {e}")
                    # Сохраняем metadata без original_data если есть проблемы с сериализацией
                    safe_metadata = {k: v for k, v in deal.metadata.items() if k != 'original_data'}
                    if safe_metadata:
                        metadata_json = json.dumps(safe_metadata, default=self._json_serializer)
            
            logger.debug(f"Создание сделки: pipeline_type={deal.pipeline_type.value}, stage_id={deal.stage_id}, tender_id={deal.tender_id}")
            result = self.db_manager.execute_query(
                query,
                (
                    deal.pipeline_type.value,
                    deal.stage_id,
                    deal.tender_id,
                    deal.name,
                    deal.description,
                    deal.amount,
                    deal.margin,
                    deal.status.value,
                    deal.tender_status_id,
                    deal.user_id,
                    metadata_json
                )
            )
            
            if result and len(result) > 0:
                deal_id = result[0].get('id')
                if deal_id:
                    logger.info(f"Сделка успешно создана с ID={deal_id}")
                    return deal_id
                else:
                    logger.warning(f"Результат запроса не содержит поле 'id': {result[0]}")
            else:
                logger.warning(f"Запрос на создание сделки выполнен, но не вернул результат. result={result}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при создании сделки: {e}", exc_info=True)
            return None
    
    def get_deals(
        self,
        pipeline_type: PipelineType,
        user_id: int,
        stage_id: Optional[int] = None
    ) -> List[Deal]:
        """Получение сделок"""
        try:
            logger.debug(f"get_deals: pipeline_type={pipeline_type.value}, user_id={user_id}, stage_id={stage_id}")
            
            if stage_id is not None:
                query = """
                    SELECT id, pipeline_type, stage_id, tender_id, name, description,
                           amount, margin, status, tender_status_id, user_id, created_at, updated_at, metadata
                    FROM sales_deals
                    WHERE pipeline_type = %s AND user_id = %s AND stage_id = %s
                    ORDER BY created_at DESC
                """
                params = (pipeline_type.value, user_id, stage_id)
            else:
                query = """
                    SELECT id, pipeline_type, stage_id, tender_id, name, description,
                           amount, margin, status, tender_status_id, user_id, created_at, updated_at, metadata
                    FROM sales_deals
                    WHERE pipeline_type = %s AND user_id = %s
                    ORDER BY created_at DESC
                """
                params = (pipeline_type.value, user_id)
            
            logger.debug(f"Выполнение запроса: {query[:100]}... с params={params}")
            results = self.db_manager.execute_query(query, params, RealDictCursor)
            logger.debug(f"Получено результатов из БД: {len(results) if results else 0}")
            # Преобразуем результаты в объекты Deal с обработкой ошибок
            deals = []
            for row in results:
                try:
                    deal = Deal(
                        id=row['id'],
                        pipeline_type=PipelineType(row['pipeline_type']),
                        stage_id=row['stage_id'],
                        tender_id=row.get('tender_id'),
                        name=row['name'],
                        description=row.get('description'),
                        amount=float(row['amount']) if row.get('amount') else None,
                        margin=float(row['margin']) if row.get('margin') else None,
                        status=DealStatus(row['status']),
                        tender_status_id=row.get('tender_status_id'),
                        user_id=row['user_id'],
                        created_at=row.get('created_at'),
                        updated_at=row.get('updated_at'),
                        metadata=self._parse_metadata(row.get('metadata'))
                    )
                    deals.append(deal)
                except Exception as e:
                    logger.error(f"Ошибка при преобразовании строки в Deal: {e}, row={dict(row)}", exc_info=True)
            
            logger.debug(f"Преобразовано сделок: {len(deals)} из {len(results) if results else 0} результатов")
            return deals
        except Exception as e:
            logger.error(f"Ошибка при получении сделок: {e}")
            return []
    
    def update_deal_stage(self, deal_id: int, new_stage_id: int) -> bool:
        """Обновление этапа сделки"""
        try:
            query = """
                UPDATE sales_deals
                SET stage_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            self.db_manager.execute_update(query, (new_stage_id, deal_id))
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении этапа сделки: {e}")
            return False
    
    def update_deal(self, deal: Deal) -> bool:
        """Обновление сделки"""
        try:
            query = """
                UPDATE sales_deals
                SET name = %s, description = %s, amount = %s, margin = %s,
                    status = %s, tender_status_id = %s, metadata = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            # Сериализуем metadata с обработкой дат
            metadata_json = None
            if deal.metadata:
                try:
                    metadata_json = json.dumps(deal.metadata, default=self._json_serializer)
                except Exception as e:
                    logger.warning(f"Ошибка при сериализации metadata, сохраняем без original_data: {e}")
                    # Сохраняем metadata без original_data если есть проблемы с сериализацией
                    safe_metadata = {k: v for k, v in deal.metadata.items() if k != 'original_data'}
                    if safe_metadata:
                        metadata_json = json.dumps(safe_metadata, default=self._json_serializer)
            self.db_manager.execute_update(
                query,
                (
                    deal.name,
                    deal.description,
                    deal.amount,
                    deal.margin,
                    deal.status.value,
                    deal.tender_status_id,
                    metadata_json,
                    deal.id
                )
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении сделки: {e}")
            return False
    
    def delete_deal(self, deal_id: int) -> bool:
        """Удаление сделки"""
        try:
            query = "DELETE FROM sales_deals WHERE id = %s"
            self.db_manager.execute_update(query, (deal_id,))
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении сделки: {e}")
            return False
    
    def is_tender_in_funnel(self, tender_id: int) -> bool:
        """Проверка, перемещена ли закупка в воронку"""
        try:
            query = """
                SELECT COUNT(*) as count
                FROM sales_deals
                WHERE tender_id = %s AND status != 'archived'
            """
            results = self.db_manager.execute_query(query, (tender_id,))
            if results:
                return results[0].get('count', 0) > 0
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке закупки в воронке: {e}")
            return False
    
    def get_tenders_in_funnels(self, user_id: int) -> List[int]:
        """Получение списка ID закупок, перемещенных в воронки"""
        try:
            query = """
                SELECT DISTINCT tender_id
                FROM sales_deals
                WHERE user_id = %s AND tender_id IS NOT NULL AND status != 'archived'
            """
            results = self.db_manager.execute_query(query, (user_id,))
            return [row['tender_id'] for row in results if row.get('tender_id')] if results else []
        except Exception as e:
            logger.error(f"Ошибка при получении закупок в воронках: {e}")
            return []

