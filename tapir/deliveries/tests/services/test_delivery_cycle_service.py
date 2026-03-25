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

    def test_isProductTypeDeliveredInWeek_cycleNoDelivery_returnsFalse(self):
        product_type = Mock()
        product_type.delivery_cycle = NO_DELIVERY[0]
        self.assertFalse(
            DeliveryCycleService.is_product_type_delivered_in_week(
                product_type=product_type, date=Mock(), cache=Mock()
            )
        )

    def test_isProductTypeDeliveredInWeek_cycleWeekly_returnsTrue(self):
        product_type = Mock()
        product_type.delivery_cycle = WEEKLY[0]
        self.assertTrue(
            DeliveryCycleService.is_product_type_delivered_in_week(
                product_type=product_type, date=Mock(), cache=Mock()
            )
        )

    @patch.object(DeliveryCycleService, "is_week_delivered_in_four_week_rhythm")
    def test_isProductTypeDeliveredInWeek_cycleEveryFourWeeksAndIsInDeliveryWeek_returnsTrue(
        self, mock_is_week_delivered_in_four_week_rhythm: Mock
    ):
        mock_is_week_delivered_in_four_week_rhythm.return_value = True
        date = Mock()
        cache = Mock()
        product_type = Mock()
        product_type.delivery_cycle = EVERY_FOUR_WEEKS[0]

        self.assertTrue(
            DeliveryCycleService.is_product_type_delivered_in_week(
                product_type=product_type, date=date, cache=cache
            )
        )

        mock_is_week_delivered_in_four_week_rhythm.assert_called_once_with(
            date=date, cache=cache
        )

    @patch.object(DeliveryCycleService, "is_week_delivered_in_four_week_rhythm")
    def test_isProductTypeDeliveredInWeek_cycleEveryFourWeeksAndIsNotInDeliveryWeek_returnsFalse(
        self, mock_is_week_delivered_in_four_week_rhythm: Mock
    ):
        mock_is_week_delivered_in_four_week_rhythm.return_value = False
        date = Mock()
        cache = Mock()

        product_type = Mock()
        product_type.delivery_cycle = EVERY_FOUR_WEEKS[0]

        self.assertFalse(
            DeliveryCycleService.is_product_type_delivered_in_week(
                product_type=product_type, date=date, cache=cache
            )
        )

        mock_is_week_delivered_in_four_week_rhythm.assert_called_once_with(
            date=date, cache=cache
        )

    def test_isProductTypeDeliveredInWeek_cycleEvenWeeksAndWeekIsEven_returnsTrue(self):
        product_type = Mock()
        product_type.delivery_cycle = EVEN_WEEKS[0]
        self.assertTrue(
            DeliveryCycleService.is_product_type_delivered_in_week(
                product_type=product_type,
                date=datetime.date(year=2025, month=1, day=6),
                cache=Mock(),
            )
        )

    def test_isProductTypeDeliveredInWeek_cycleEvenWeeksAndWeekIsOdd_returnsFalse(self):
        product_type = Mock()
        product_type.delivery_cycle = EVEN_WEEKS[0]
        self.assertFalse(
            DeliveryCycleService.is_product_type_delivered_in_week(
                product_type=product_type,
                date=datetime.date(year=2025, month=1, day=13),
                cache=Mock(),
            )
        )

    def test_isProductTypeDeliveredInWeek_cycleOddWeeksAndWeekIsEven_returnsFalse(self):
        product_type = Mock()
        product_type.delivery_cycle = ODD_WEEKS[0]
        self.assertFalse(
            DeliveryCycleService.is_product_type_delivered_in_week(
                product_type=product_type,
                date=datetime.date(year=2025, month=1, day=6),
                cache=Mock(),
            )
        )

    def test_isProductTypeDeliveredInWeek_cycleOddWeeksAndWeekIsOdd_returnsTrue(self):
        product_type = Mock()
        product_type.delivery_cycle = ODD_WEEKS[0]
        self.assertTrue(
            DeliveryCycleService.is_product_type_delivered_in_week(
                product_type=product_type,
                date=datetime.date(year=2025, month=1, day=13),
                cache=Mock(),
            )
        )
