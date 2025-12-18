"""
Сервис синхронизации данных сделок с реестром закупок
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from psycopg2.extras import RealDictCursor
from modules.crm.sales_funnel.models import Deal
from modules.crm.sales_funnel.deal_repository import DealRepository
from services.tender_repository import TenderRepository


class DealSyncService:
    """Сервис для синхронизации данных сделок с реестром закупок"""
    
    def __init__(
        self,
        deal_repo: DealRepository,
        tender_repo: TenderRepository
    ):
        self.deal_repo = deal_repo
        self.tender_repo = tender_repo
    
    def sync_deal_with_tender(self, deal: Deal) -> bool:
        """
        Синхронизация данных сделки с реестром закупок
        
        Args:
            deal: Сделка для синхронизации
            
        Returns:
            True если обновление успешно
        """
        if not deal.tender_id:
            return False
        
        try:
            # Получаем актуальные данные закупки из реестра
            registry_type = deal.metadata.get('registry_type') if deal.metadata else None
            if not registry_type:
                logger.warning(f"Не указан registry_type для сделки {deal.id}")
                return False
            
            # Получаем данные закупки
            tender_data = self._get_tender_data(deal.tender_id, registry_type)
            if not tender_data:
                logger.warning(f"Закупка {deal.tender_id} не найдена в реестре {registry_type}")
                return False
            
            # Обновляем метаданные сделки актуальными данными
            updated_metadata = deal.metadata.copy() if deal.metadata else {}
            updated_metadata['original_data'] = tender_data
            updated_metadata['last_sync'] = datetime.now().isoformat()
            
            deal.metadata = updated_metadata
            
            # Обновляем сумму, если она изменилась
            new_amount = self._extract_amount(tender_data)
            if new_amount and new_amount != deal.amount:
                deal.amount = new_amount
                logger.info(f"Обновлена сумма сделки {deal.id}: {deal.amount} -> {new_amount}")
            
            # Обновляем статус закупки из реестра
            new_status_id = tender_data.get('status_id')
            if new_status_id and new_status_id != deal.tender_status_id:
                old_status = deal.tender_status_id
                deal.tender_status_id = new_status_id
                logger.info(f"Обновлен статус закупки для сделки {deal.id}: {old_status} -> {new_status_id}")
            
            # Обновляем описание
            deal.description = self._generate_deal_description(tender_data, registry_type)
            
            # Сохраняем обновленную сделку
            return self.deal_repo.update_deal(deal)
            
        except Exception as e:
            logger.error(f"Ошибка при синхронизации сделки {deal.id}: {e}", exc_info=True)
            return False
    
    def sync_all_deals_with_tenders(self, user_id: int) -> Dict[str, int]:
        """
        Синхронизация всех сделок пользователя с реестром
        
        Returns:
            Словарь с результатами: {'synced': count, 'errors': count}
        """
        result = {'synced': 0, 'errors': 0}
        
        try:
            # Получаем все сделки пользователя с привязанными закупками
            from modules.crm.sales_funnel.models import PipelineType
            
            for pipeline_type in PipelineType:
                deals = self.deal_repo.get_deals(pipeline_type, user_id)
                for deal in deals:
                    if deal.tender_id:
                        if self.sync_deal_with_tender(deal):
                            result['synced'] += 1
                        else:
                            result['errors'] += 1
            
            logger.info(f"Синхронизация завершена: обновлено {result['synced']}, ошибок {result['errors']}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при синхронизации всех сделок: {e}", exc_info=True)
            result['errors'] += 1
            return result
    
    def _get_tender_data(self, tender_id: int, registry_type: str) -> Optional[Dict[str, Any]]:
        """Получение данных закупки из реестра"""
        try:
            if registry_type == '44fz':
                # Получаем из реестра 44ФЗ
                query = """
                    SELECT r.*, c.customer_full_name as customer_full_name, c.customer_short_name as customer_short_name,
                           cont.full_name as contractor_full_name, cont.short_name as contractor_short_name,
                           reg.name as region_name, okpd.main_code as okpd_main_code,
                           okpd.sub_code as okpd_sub_code, okpd.name as okpd_name,
                           tp.trading_platform_name as platform_name
                    FROM reestr_contract_44_fz r
                    LEFT JOIN customer c ON r.customer_id = c.id
                    LEFT JOIN region reg ON r.region_id = reg.id
                    LEFT JOIN contractor cont ON r.contractor_id = cont.id
                    LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
                    LEFT JOIN trading_platform tp ON r.trading_platform_id = tp.id
                    WHERE r.id = %s
                """
            else:  # 223fz
                query = """
                    SELECT r.*, c.customer_full_name as customer_full_name, c.customer_short_name as customer_short_name,
                           cont.full_name as contractor_full_name, cont.short_name as contractor_short_name,
                           reg.name as region_name, okpd.main_code as okpd_main_code,
                           okpd.sub_code as okpd_sub_code, okpd.name as okpd_name,
                           tp.trading_platform_name as platform_name
                    FROM reestr_contract_223_fz r
                    LEFT JOIN customer c ON r.customer_id = c.id
                    LEFT JOIN region reg ON r.region_id = reg.id
                    LEFT JOIN contractor cont ON r.contractor_id = cont.id
                    LEFT JOIN collection_codes_okpd okpd ON r.okpd_id = okpd.id
                    LEFT JOIN trading_platform tp ON r.trading_platform_id = tp.id
                    WHERE r.id = %s
                """
            
            results = self.deal_repo.db_manager.execute_query(
                query,
                (tender_id,),
                RealDictCursor
            )
            
            if results:
                return dict(results[0])
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных закупки {tender_id}: {e}")
            return None
    
    def _extract_amount(self, tender_data: Dict[str, Any]) -> Optional[float]:
        """Извлечение суммы закупки"""
        amount = tender_data.get('final_price') or tender_data.get('initial_price') or tender_data.get('nmck')
        if amount:
            try:
                return float(amount)
            except (ValueError, TypeError):
                pass
        return None
    
    def _generate_deal_description(
        self,
        tender_data: Dict[str, Any],
        registry_type: str
    ) -> str:
        """Генерация описания сделки"""
        parts = [f"Реестр: {registry_type.upper()}"]
        
        customer = tender_data.get('customer_full_name') or tender_data.get('customer_short_name')
        if customer:
            parts.append(f"Заказчик: {customer}")
        
        region = tender_data.get('region_name')
        if region:
            parts.append(f"Регион: {region}")
        
        return "\n".join(parts)

