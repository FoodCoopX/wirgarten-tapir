from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.deliveries.services.joker_management_service import JokerManagementService


class TestJokerManagementServiceGetDateLimitForJokerChanges(SimpleTestCase):
    @patch.object(
        DateLimitForDeliveryChangeCalculator,
        "calculate_date_limit_for_delivery_changes_in_week",
    )
    def test_getDateLimitForJokerChanges_default_callsService(
        self, mock_calculate_date_limit_for_delivery_changes_in_week: Mock
    ):
        input_date = Mock()
        limit_date = Mock()
        mock_calculate_date_limit_for_delivery_changes_in_week.return_value = limit_date

        cache = {}
        result = JokerManagementService.get_date_limit_for_joker_changes(
            input_date, cache=cache
        )

        self.assertEqual(limit_date, result)
        mock_calculate_date_limit_for_delivery_changes_in_week.assert_called_once_with(
            input_date, cache=cache
        )
