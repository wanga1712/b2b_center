"""
Модуль воронок продаж
"""

from modules.crm.sales_funnel.models import (
    PipelineType,
    DealStatus,
    PipelineStage,
    Deal
)
from modules.crm.sales_funnel.pipeline_repository import PipelineRepository
from modules.crm.sales_funnel.deal_repository import DealRepository

__all__ = [
    'PipelineType',
    'DealStatus',
    'PipelineStage',
    'Deal',
    'PipelineRepository',
    'DealRepository',
]

