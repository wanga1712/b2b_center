"""
Тесты для DealDetailService (агрегация данных карточки сделки).
"""

from unittest.mock import Mock

from psycopg2.extras import RealDictCursor

from modules.crm.sales_funnel.deal_detail_service import DealDetailService
from modules.crm.sales_funnel.models import Deal, PipelineType, DealStatus


def make_deal_with_metadata() -> Deal:
    """Хелпер для создания тестовой сделки."""
    return Deal(
        id=1,
        pipeline_type=PipelineType.MATERIALS_SUPPLY,
        stage_id=8,
        tender_id=518801,
        name="Закупка (№518801)",
        description=None,
        amount=1000.0,
        margin=10.0,
        status=DealStatus.ACTIVE,
        tender_status_id=1,
        user_id=1,
        created_at=None,
        updated_at=None,
        metadata={
            "registry_type": "44fz",
            "tender_id": 518801,
            "original_data": {
                "id": 42,
                "registry_type": "44fz",
                "tender_id": 518801,
                "customer_id": 10,
                "contractor_id": 20,
                "customer_full_name": "Тестовый заказчик",
                "contractor_full_name": "Тестовый подрядчик",
            },
        },
    )


class TestDealDetailService:
    """Тесты сервиса DealDetailService."""

    def test_build_deal_card_basic(self):
        """Сборка карточки сделки с минимальными данными."""
        mock_db = Mock()
        # По умолчанию ничего не возвращаем (контакты и товары пустые списки)
        mock_db.execute_query.return_value = []

        service = DealDetailService(mock_db)
        deal = make_deal_with_metadata()

        card = service.build_deal_card(deal)

        assert card["deal"]["id"] == 1
        assert card["deal"]["pipeline_type"] == PipelineType.MATERIALS_SUPPLY.value
        assert card["tender"]["tender_id"] == 518801
        assert card["tender"]["customer_full_name"] == "Тестовый заказчик"
        assert card["tender"]["contractor_full_name"] == "Тестовый подрядчик"
        assert card["contacts"]["customer"] == []
        assert card["contacts"]["contractor"] == []
        assert card["contacts"]["deal"] == []
        assert card["items"] == []

    def test_load_contacts_by_filter(self, monkeypatch):
        """Проверка выборки контактов по фильтрам."""
        rows = [
            {
                "contact_id": 1,
                "full_name": "Иванов Иван",
                "department": "Снабжение",
                "position": "Менеджер",
                "phone_mobile": "+7 900 000-00-00",
                "email": "test@example.com",
                "role": "ЛПР",
                "is_primary": True,
                "customer_id": 10,
                "contractor_id": None,
                "deal_id": 1,
            }
        ]

        mock_db = Mock()
        mock_db.execute_query.return_value = rows

        service = DealDetailService(mock_db)
        result = service._load_contacts_by_filter(customer_id=10)

        assert len(result) == 1
        assert result[0]["full_name"] == "Иванов Иван"
        mock_db.execute_query.assert_called_once()


