import datetime
from unittest.mock import patch, MagicMock

from tapir.deliveries.services.joker_value_service import JokerValueService
from tapir.deliveries.services.member_specific_delivery_day_calculator import (
    MemberSpecificDeliveryDayCalculator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetActualDeliveryDate(TapirUnitTest):
    @patch.object(
        MemberSpecificDeliveryDayCalculator,
        "get_specific_delivery_date",
        autospec=True,
        return_value=datetime.date(year=2026, month=10, day=1),
    )
    @patch(
        "tapir.deliveries.services.joker_value_service.get_next_delivery_date",
        autospec=True,
        return_value=datetime.date(year=2026, month=9, day=30),
    )
    def test_getActualDeliveryDate_default_returnsMemberSpecificDeliveryDateOfJokerWeek(
        self,
        mock_get_next_delivery_date: MagicMock,
        mock_get_specific_delivery_date: MagicMock,
    ):
        cache = {}

        result = JokerValueService.get_actual_delivery_date(
            member_id="test_member_id",
            joker_date=datetime.date(year=2026, month=9, day=30),
            cache=cache,
        )

        self.assertEqual(datetime.date(year=2026, month=10, day=1), result)
        mock_get_next_delivery_date.assert_called_once_with(
            datetime.date(year=2026, month=9, day=28), cache=cache
        )
        mock_get_specific_delivery_date.assert_called_once_with(
            member_id="test_member_id",
            delivery_date=datetime.date(year=2026, month=9, day=30),
            cache=cache,
        )
