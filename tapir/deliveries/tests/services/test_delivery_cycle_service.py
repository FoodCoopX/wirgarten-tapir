import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.deliveries.services.delivery_cycle_service import DeliveryCycleService
from tapir.wirgarten.constants import (
    NO_DELIVERY,
    WEEKLY,
    EVERY_FOUR_WEEKS,
    EVEN_WEEKS,
    ODD_WEEKS,
)
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestDeliveryCycleService(SimpleTestCase):
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

    def test_isCycleDeliveredInWeek_cycleNoDelivery_returnsFalse(self):
        self.assertFalse(
            DeliveryCycleService.is_cycle_delivered_in_week(
                NO_DELIVERY[0], date=Mock(), cache=Mock()
            )
        )

    def test_isCycleDeliveredInWeek_cycleWeekly_returnsTrue(self):
        self.assertTrue(
            DeliveryCycleService.is_cycle_delivered_in_week(
                WEEKLY[0], date=Mock(), cache=Mock()
            )
        )

    @patch.object(DeliveryCycleService, "is_week_delivered_in_four_week_rhythm")
    def test_isCycleDeliveredInWeek_cycleEveryFourWeeksAndIsInDeliveryWeek_returnsTrue(
        self, mock_is_week_delivered_in_four_week_rhythm: Mock
    ):
        mock_is_week_delivered_in_four_week_rhythm.return_value = True
        date = Mock()
        cache = Mock()

        self.assertTrue(
            DeliveryCycleService.is_cycle_delivered_in_week(
                EVERY_FOUR_WEEKS[0], date=date, cache=cache
            )
        )

        mock_is_week_delivered_in_four_week_rhythm.assert_called_once_with(
            date=date, cache=cache
        )

    @patch.object(DeliveryCycleService, "is_week_delivered_in_four_week_rhythm")
    def test_isCycleDeliveredInWeek_cycleEveryFourWeeksAndIsNotInDeliveryWeek_returnsFalse(
        self, mock_is_week_delivered_in_four_week_rhythm: Mock
    ):
        mock_is_week_delivered_in_four_week_rhythm.return_value = False
        date = Mock()
        cache = Mock()

        self.assertFalse(
            DeliveryCycleService.is_cycle_delivered_in_week(
                EVERY_FOUR_WEEKS[0], date=date, cache=cache
            )
        )

        mock_is_week_delivered_in_four_week_rhythm.assert_called_once_with(
            date=date, cache=cache
        )

    def test_isCycleDeliveredInWeek_cycleEvenWeeksAndWeekIsEven_returnsTrue(self):
        self.assertTrue(
            DeliveryCycleService.is_cycle_delivered_in_week(
                EVEN_WEEKS[0],
                date=datetime.date(year=2025, month=1, day=6),
                cache=Mock(),
            )
        )

    def test_isCycleDeliveredInWeek_cycleEvenWeeksAndWeekIsOdd_returnsFalse(self):
        self.assertFalse(
            DeliveryCycleService.is_cycle_delivered_in_week(
                EVEN_WEEKS[0],
                date=datetime.date(year=2025, month=1, day=13),
                cache=Mock(),
            )
        )

    def test_isCycleDeliveredInWeek_cycleOddWeeksAndWeekIsEven_returnsFalse(self):
        self.assertFalse(
            DeliveryCycleService.is_cycle_delivered_in_week(
                ODD_WEEKS[0],
                date=datetime.date(year=2025, month=1, day=6),
                cache=Mock(),
            )
        )

    def test_isCycleDeliveredInWeek_cycleOddWeeksAndWeekIsOdd_returnsTrue(self):
        self.assertTrue(
            DeliveryCycleService.is_cycle_delivered_in_week(
                ODD_WEEKS[0],
                date=datetime.date(year=2025, month=1, day=13),
                cache=Mock(),
            )
        )

    @patch("tapir.deliveries.services.delivery_cycle_service.get_parameter_value")
    def test_getCyclesDeliveredInWeek_default_returnsCorrectValues(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = datetime.date(year=2025, month=1, day=6)
        cache = {}

        self.assertEqual(
            [WEEKLY[0], EVEN_WEEKS[0], EVERY_FOUR_WEEKS[0]],
            DeliveryCycleService.get_cycles_delivered_in_week(
                date=datetime.date(year=2025, month=1, day=6),
                cache=cache,
            ),
        )

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_FOUR_WEEK_CYCLE_START_POINT, cache=cache
        )

    @patch("tapir.deliveries.services.delivery_cycle_service.get_parameter_value")
    def test_getCyclesDeliveredInWeek_default2_returnsCorrectValues(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = datetime.date(year=2025, month=1, day=6)
        cache = {}

        self.assertEqual(
            [WEEKLY[0], ODD_WEEKS[0]],
            DeliveryCycleService.get_cycles_delivered_in_week(
                date=datetime.date(year=2025, month=1, day=13),
                cache=cache,
            ),
        )

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_FOUR_WEEK_CYCLE_START_POINT, cache=cache
        )
