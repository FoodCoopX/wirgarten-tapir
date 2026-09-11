import datetime
from unittest.mock import patch, Mock

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.deliveries.services.delivery_cycle_service import DeliveryCycleService
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestIsWeekDeliveredInFourWeekRhythm(TapirUnitTest):
    @patch("tapir.deliveries.services.delivery_cycle_service.get_parameter_value")
    def test_isWeekDeliveredInFourWeekRhythm_dateInThePastAndFourWeeksAgo_returnsTrue(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = datetime.date(year=2025, month=1, day=6)
        cache = {}

        self.assertTrue(
            DeliveryCycleService.is_week_delivered_in_four_week_rhythm(
                date=datetime.date(year=2024, month=12, day=13), cache=cache
            )
        )

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_FOUR_WEEK_CYCLE_START_POINT, cache=cache
        )

    @patch("tapir.deliveries.services.delivery_cycle_service.get_parameter_value")
    def test_isWeekDeliveredInFourWeekRhythm_dateInThePastAndThreeWeeksAgo_returnsTrue(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = datetime.date(year=2025, month=1, day=6)
        cache = {}

        self.assertFalse(
            DeliveryCycleService.is_week_delivered_in_four_week_rhythm(
                date=datetime.date(year=2024, month=12, day=16), cache=cache
            )
        )

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_FOUR_WEEK_CYCLE_START_POINT, cache=cache
        )

    @patch("tapir.deliveries.services.delivery_cycle_service.get_parameter_value")
    def test_isWeekDeliveredInFourWeekRhythm_dateIsInSameWeek_returnsTrue(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = datetime.date(year=2025, month=1, day=6)
        cache = {}

        self.assertTrue(
            DeliveryCycleService.is_week_delivered_in_four_week_rhythm(
                date=datetime.date(year=2025, month=1, day=12), cache=cache
            )
        )

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_FOUR_WEEK_CYCLE_START_POINT, cache=cache
        )

    @patch("tapir.deliveries.services.delivery_cycle_service.get_parameter_value")
    def test_isWeekDeliveredInFourWeekRhythm_dateIsOneWeekLater_returnsFalse(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = datetime.date(year=2025, month=1, day=6)
        cache = {}

        self.assertFalse(
            DeliveryCycleService.is_week_delivered_in_four_week_rhythm(
                date=datetime.date(year=2025, month=1, day=13), cache=cache
            )
        )

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_FOUR_WEEK_CYCLE_START_POINT, cache=cache
        )
