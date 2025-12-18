"""
Репозиторий для работы с воронками продаж в БД
"""

from typing import List, Optional
from loguru import logger
from core.tender_database import TenderDatabaseManager
from psycopg2.extras import RealDictCursor
from modules.crm.sales_funnel.models import PipelineType, PipelineStage


class PipelineRepository:
    """Репозиторий для работы с этапами воронок"""
    
    def __init__(self, db_manager: TenderDatabaseManager):
        self.db_manager = db_manager
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Создание таблиц, если их нет"""
        try:
            # Проверяем подключение к БД
            if not self.db_manager.is_connected():
                logger.error("Нет подключения к базе данных tender_monitor для создания таблиц воронок")
                return
            
            logger.info("Проверка и создание таблиц для воронок продаж в базе tender_monitor...")
            
            # Таблица этапов воронок
            query = """
                CREATE TABLE IF NOT EXISTS sales_pipeline_stages (
                    id SERIAL PRIMARY KEY,
                    pipeline_type VARCHAR(50) NOT NULL,
                    stage_order INTEGER NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(pipeline_type, stage_order)
                )
            """
            self.db_manager.execute_update(query)
            logger.debug("Таблица sales_pipeline_stages проверена/создана")
            
            # Таблица сделок
            query = """
                CREATE TABLE IF NOT EXISTS sales_deals (
                    id SERIAL PRIMARY KEY,
                    pipeline_type VARCHAR(50) NOT NULL,
                    stage_id INTEGER NOT NULL REFERENCES sales_pipeline_stages(id),
                    tender_id INTEGER,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    amount DECIMAL(15, 2),
                    margin DECIMAL(10, 2),
                    status VARCHAR(20) DEFAULT 'active',
                    tender_status_id INTEGER,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB
                )
            """
            self.db_manager.execute_update(query)
            logger.debug("Таблица sales_deals проверена/создана")
            
            # Добавляем поле tender_status_id, если его нет (миграция)
            try:
                self.db_manager.execute_update("""
                    ALTER TABLE sales_deals 
                    ADD COLUMN IF NOT EXISTS tender_status_id INTEGER
                """)
                logger.debug("Поле tender_status_id проверено/добавлено")
            except Exception as e:
                logger.warning(f"Не удалось добавить поле tender_status_id (возможно, уже существует): {e}")
            
            # Создаем индексы
            try:
                self.db_manager.execute_update(
                    "CREATE INDEX IF NOT EXISTS idx_deals_pipeline_type ON sales_deals(pipeline_type)"
                )
                self.db_manager.execute_update(
                    "CREATE INDEX IF NOT EXISTS idx_deals_stage_id ON sales_deals(stage_id)"
                )
                self.db_manager.execute_update(
                    "CREATE INDEX IF NOT EXISTS idx_deals_user_id ON sales_deals(user_id)"
                )
                logger.debug("Индексы для sales_deals проверены/созданы")
            except Exception as e:
                logger.warning(f"Ошибка при создании индексов: {e}")
            
            # Инициализируем этапы по умолчанию
            self._init_default_stages()
            
            logger.info("Таблицы для воронок продаж успешно проверены/созданы в базе tender_monitor")
            
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц воронок продаж: {e}", exc_info=True)
    
    def _init_default_stages(self):
        """Инициализация этапов по умолчанию"""
        try:
            # Проверяем, есть ли уже этапы
            existing = self.db_manager.execute_query(
                "SELECT COUNT(*) as count FROM sales_pipeline_stages"
            )
            if existing and existing[0].get('count', 0) > 0:
                return  # Этапы уже созданы
            
            # Этапы для участия в торгах
            participation_stages = [
                (0, "Импорт и первичный фильтр"),
                (1, "Предварительный интерес"),
                (2, "Быстрый экономический скрининг"),
                (3, "Полный расчёт сметы"),
                (4, "Второе решение об участии"),
                (5, "Подготовка и подача заявки"),
                (6, "Торги/переторжка и результат"),
            ]
            
            # Этапы для поставки материалов
            materials_stages = [
                (1, "Совпадение по материалам"),
                (2, "Расчет коммерческого предложения"),
                (3, "Переговоры и согласование"),
                (4, "Заказ и отгрузки"),
            ]
            
            # Этапы для субподрядных работ
            subcontracting_stages = [
                (1, "Попадание в периметр компетенций"),
                (2, "Черновой расчёт стоимости работ"),
                (3, "Детальная калькуляция и ресурсное планирование"),
                (4, "Коммерческое предложение по работам"),
                (5, "Договор субподряда и выполнение"),
            ]
            
            for stage_order, name in participation_stages:
                self.db_manager.execute_update(
                    "INSERT INTO sales_pipeline_stages (pipeline_type, stage_order, name) VALUES (%s, %s, %s)",
                    (PipelineType.PARTICIPATION.value, stage_order, name)
                )
            
            for stage_order, name in materials_stages:
                self.db_manager.execute_update(
                    "INSERT INTO sales_pipeline_stages (pipeline_type, stage_order, name) VALUES (%s, %s, %s)",
                    (PipelineType.MATERIALS_SUPPLY.value, stage_order, name)
                )
            
            for stage_order, name in subcontracting_stages:
                self.db_manager.execute_update(
                    "INSERT INTO sales_pipeline_stages (pipeline_type, stage_order, name) VALUES (%s, %s, %s)",
                    (PipelineType.SUBCONTRACTING.value, stage_order, name)
                )
            
            logger.info("Этапы воронок продаж инициализированы")
        except Exception as e:
            logger.error(f"Ошибка при инициализации этапов: {e}")
    
    def get_stages(self, pipeline_type: PipelineType) -> List[PipelineStage]:
        """Получение всех этапов воронки"""
        try:
            query = """
                SELECT id, pipeline_type, stage_order, name, description, created_at, updated_at
                FROM sales_pipeline_stages
                WHERE pipeline_type = %s
                ORDER BY stage_order ASC
            """
            results = self.db_manager.execute_query(
                query,
                (pipeline_type.value,),
                RealDictCursor
            )
            return [
                PipelineStage(
                    id=row['id'],
                    pipeline_type=PipelineType(row['pipeline_type']),
                    stage_order=row['stage_order'],
                    name=row['name'],
                    description=row.get('description'),
                    created_at=row.get('created_at'),
                    updated_at=row.get('updated_at')
                )
                for row in results
            ]
        except Exception as e:
            logger.error(f"Ошибка при получении этапов: {e}")
            return []

