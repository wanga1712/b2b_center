"""
Модели данных для воронок продаж
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PipelineType(Enum):
    """Тип воронки продаж"""
    PARTICIPATION = "participation"  # Участие в торгах
    MATERIALS_SUPPLY = "materials_supply"  # Поставка материалов
    SUBCONTRACTING = "subcontracting"  # Субподрядные работы


class DealStatus(Enum):
    """Статус сделки"""
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    ARCHIVED = "archived"


@dataclass
class PipelineStage:
    """Этап воронки продаж"""
    id: Optional[int]
    pipeline_type: PipelineType
    stage_order: int  # Порядок этапа (0, 1, 2, ...)
    name: str  # Название этапа
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Deal:
    """Сделка в воронке продаж"""
    id: Optional[int]
    pipeline_type: PipelineType
    stage_id: int
    name: str  # Название сделки
    tender_id: Optional[int] = None  # Связь с торгом (если есть)
    description: Optional[str] = None
    amount: Optional[float] = None  # Сумма сделки
    margin: Optional[float] = None  # Маржа
    status: DealStatus = DealStatus.ACTIVE
    tender_status_id: Optional[int] = None  # Статус закупки из реестра (1=новые, 2=работа комиссии, 3=разыгранные)
    user_id: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None  # Дополнительные данные (JSON)

