"""
Сервис для перемещения закупки в воронку продаж
"""

from typing import Optional, Dict, Any
from loguru import logger
from modules.crm.sales_funnel.models import PipelineType, Deal, DealStatus
from modules.crm.sales_funnel.pipeline_repository import PipelineRepository
from modules.crm.sales_funnel.deal_repository import DealRepository


class TenderToFunnelService:
    """Сервис для перемещения закупки в воронку продаж"""
    
    def __init__(
        self,
        pipeline_repo: PipelineRepository,
        deal_repo: DealRepository
    ):
        self.pipeline_repo = pipeline_repo
        self.deal_repo = deal_repo
    
    def move_tender_to_funnel(
        self,
        tender_id: int,
        registry_type: str,
        pipeline_type: PipelineType,
        user_id: int,
        tender_data: Dict[str, Any]
    ) -> Optional[int]:
        """
        Перемещение закупки в воронку продаж
        
        Args:
            tender_id: ID закупки
            registry_type: Тип реестра (44fz/223fz)
            pipeline_type: Тип воронки
            user_id: ID пользователя
            tender_data: Данные закупки
            
        Returns:
            ID созданной сделки или None при ошибке
        """
        try:
            # Получаем первый этап выбранной воронки
            stages = self.pipeline_repo.get_stages(pipeline_type)
            if not stages:
                logger.error(f"Этапы для воронки {pipeline_type.value} не найдены")
                return None
            
            # Первый этап - с минимальным stage_order
            first_stage = min(stages, key=lambda s: s.stage_order)
            
            # Формируем название сделки из данных закупки
            deal_name = self._generate_deal_name(tender_data)
            
            # Извлекаем статус закупки из реестра
            tender_status_id = tender_data.get('status_id')
            
            # Создаем сделку
            deal = Deal(
                id=None,
                pipeline_type=pipeline_type,
                stage_id=first_stage.id,
                name=deal_name,
                tender_id=tender_id,
                description=self._generate_deal_description(tender_data, registry_type),
                amount=self._extract_amount(tender_data),
                user_id=user_id,
                status=DealStatus.ACTIVE,
                tender_status_id=tender_status_id,
                metadata={
                    'registry_type': registry_type,
                    'tender_id': tender_id,
                    'original_data': tender_data
                }
            )
            
            deal_id = self.deal_repo.create_deal(deal)
            if deal_id:
                logger.info(
                    f"Закупка {tender_id} ({registry_type}) перемещена в воронку "
                    f"{pipeline_type.value}, создана сделка ID={deal_id}"
                )
                return deal_id
            else:
                logger.error(f"Не удалось создать сделку для закупки {tender_id}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при перемещении закупки в воронку: {e}", exc_info=True)
            return None
    
    def _generate_deal_name(self, tender_data: Dict[str, Any]) -> str:
        """Генерация названия сделки из данных закупки"""
        name = tender_data.get('name') or tender_data.get('subject') or 'Закупка'
        number = tender_data.get('number') or tender_data.get('id')
        if number:
            return f"{name} (№{number})"
        return name
    
    def _generate_deal_description(
        self,
        tender_data: Dict[str, Any],
        registry_type: str
    ) -> str:
        """Генерация описания сделки"""
        parts = [f"Реестр: {registry_type.upper()}"]
        
        customer = tender_data.get('customer') or tender_data.get('customer_name')
        if customer:
            parts.append(f"Заказчик: {customer}")
        
        region = tender_data.get('region') or tender_data.get('region_name')
        if region:
            parts.append(f"Регион: {region}")
        
        return "\n".join(parts)
    
    def _extract_amount(self, tender_data: Dict[str, Any]) -> Optional[float]:
        """Извлечение суммы закупки"""
        amount = tender_data.get('nmck') or tender_data.get('price') or tender_data.get('amount')
        if amount:
            try:
                return float(amount)
            except (ValueError, TypeError):
                pass
        return None

