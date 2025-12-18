"""
Тесты для моделей воронок продаж
"""

import pytest
from datetime import datetime
from modules.crm.sales_funnel.models import (
    PipelineType,
    DealStatus,
    PipelineStage,
    Deal
)


class TestPipelineType:
    """Тесты для типа воронки"""
    
    def test_pipeline_type_values(self):
        """Проверка значений типов воронок"""
        assert PipelineType.PARTICIPATION.value == "participation"
        assert PipelineType.MATERIALS_SUPPLY.value == "materials_supply"
        assert PipelineType.SUBCONTRACTING.value == "subcontracting"


class TestDealStatus:
    """Тесты для статуса сделки"""
    
    def test_deal_status_values(self):
        """Проверка значений статусов"""
        assert DealStatus.ACTIVE.value == "active"
        assert DealStatus.WON.value == "won"
        assert DealStatus.LOST.value == "lost"
        assert DealStatus.ARCHIVED.value == "archived"


class TestPipelineStage:
    """Тесты для этапа воронки"""
    
    def test_create_pipeline_stage(self):
        """Создание этапа воронки"""
        stage = PipelineStage(
            id=1,
            pipeline_type=PipelineType.PARTICIPATION,
            stage_order=0,
            name="Импорт и первичный фильтр",
            description="Автоматический этап"
        )
        assert stage.id == 1
        assert stage.pipeline_type == PipelineType.PARTICIPATION
        assert stage.stage_order == 0
        assert stage.name == "Импорт и первичный фильтр"
        assert stage.description == "Автоматический этап"
    
    def test_pipeline_stage_without_description(self):
        """Создание этапа без описания"""
        stage = PipelineStage(
            id=2,
            pipeline_type=PipelineType.MATERIALS_SUPPLY,
            stage_order=1,
            name="Совпадение по материалам"
        )
        assert stage.description is None


class TestDeal:
    """Тесты для сделки"""
    
    def test_create_deal(self):
        """Создание сделки"""
        deal = Deal(
            id=1,
            pipeline_type=PipelineType.PARTICIPATION,
            stage_id=2,
            tender_id=123,
            name="Сделка по торгу 123",
            amount=1000000.0,
            margin=15.5,
            status=DealStatus.ACTIVE,
            user_id=1
        )
        assert deal.id == 1
        assert deal.pipeline_type == PipelineType.PARTICIPATION
        assert deal.stage_id == 2
        assert deal.tender_id == 123
        assert deal.name == "Сделка по торгу 123"
        assert deal.amount == 1000000.0
        assert deal.margin == 15.5
        assert deal.status == DealStatus.ACTIVE
        assert deal.user_id == 1
    
    def test_deal_with_metadata(self):
        """Создание сделки с метаданными"""
        metadata = {"tender_name": "Торг 123", "region": "Москва"}
        deal = Deal(
            id=2,
            pipeline_type=PipelineType.MATERIALS_SUPPLY,
            stage_id=1,
            name="Поставка материалов",
            metadata=metadata
        )
        assert deal.metadata == metadata

