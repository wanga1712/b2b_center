"""
Тесты для репозиториев воронок продаж
"""

import pytest
from unittest.mock import Mock, MagicMock
from modules.crm.sales_funnel.models import PipelineType, PipelineStage, Deal, DealStatus
from modules.crm.sales_funnel.pipeline_repository import PipelineRepository
from modules.crm.sales_funnel.deal_repository import DealRepository


class TestPipelineRepository:
    """Тесты для репозитория этапов"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Мок менеджера БД"""
        db = Mock()
        db.execute_query = Mock(return_value=[])
        db.execute_update = Mock()
        return db
    
    @pytest.fixture
    def pipeline_repo(self, mock_db_manager):
        """Создание репозитория"""
        return PipelineRepository(mock_db_manager)
    
    def test_get_stages(self, pipeline_repo, mock_db_manager):
        """Получение этапов воронки"""
        # Мокируем результат запроса
        mock_db_manager.execute_query.return_value = [
            {
                'id': 1,
                'pipeline_type': 'participation',
                'stage_order': 0,
                'name': 'Импорт и первичный фильтр',
                'description': None,
                'created_at': None,
                'updated_at': None
            }
        ]
        
        stages = pipeline_repo.get_stages(PipelineType.PARTICIPATION)
        
        assert len(stages) == 1
        assert stages[0].id == 1
        assert stages[0].pipeline_type == PipelineType.PARTICIPATION
        assert stages[0].name == "Импорт и первичный фильтр"


class TestDealRepository:
    """Тесты для репозитория сделок"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Мок менеджера БД"""
        db = Mock()
        db.execute_query = Mock(return_value=[])
        db.execute_update = Mock()
        return db
    
    @pytest.fixture
    def deal_repo(self, mock_db_manager):
        """Создание репозитория"""
        return DealRepository(mock_db_manager)
    
    def test_create_deal(self, deal_repo, mock_db_manager):
        """Создание сделки"""
        deal = Deal(
            id=None,
            pipeline_type=PipelineType.PARTICIPATION,
            stage_id=1,
            name="Тестовая сделка",
            user_id=1
        )
        
        # Мокируем возврат ID
        mock_db_manager.execute_query.return_value = [{'id': 123}]
        
        deal_id = deal_repo.create_deal(deal)
        
        assert deal_id == 123
        mock_db_manager.execute_query.assert_called_once()
    
    def test_get_deals(self, deal_repo, mock_db_manager):
        """Получение сделок"""
        mock_db_manager.execute_query.return_value = [
            {
                'id': 1,
                'pipeline_type': 'participation',
                'stage_id': 1,
                'tender_id': 123,
                'name': 'Тестовая сделка',
                'description': None,
                'amount': 1000000.0,
                'margin': 15.5,
                'status': 'active',
                'user_id': 1,
                'created_at': None,
                'updated_at': None,
                'metadata': None
            }
        ]
        
        deals = deal_repo.get_deals(PipelineType.PARTICIPATION, user_id=1)
        
        assert len(deals) == 1
        assert deals[0].id == 1
        assert deals[0].name == "Тестовая сделка"
        assert deals[0].amount == 1000000.0
    
    def test_update_deal_stage(self, deal_repo, mock_db_manager):
        """Обновление этапа сделки"""
        result = deal_repo.update_deal_stage(deal_id=1, new_stage_id=2)
        
        assert result is True
        mock_db_manager.execute_update.assert_called_once()

