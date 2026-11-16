import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from tapir.bidding_round.services.bidding_round_delivery_charge_service import (
    BiddingRoundDeliveryChargeService,
)
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest

START_DATE = datetime.date(2026, 1, 1)
END_DATE = datetime.date(2026, 1, 31)


def _build_growing_period(start_date=START_DATE, end_date=END_DATE):
    growing_period = Mock()
    growing_period.start_date = start_date
    growing_period.end_date = end_date
    return growing_period


class TestBiddingRoundDeliveryChargeService(TapirUnitTest):
    @patch.object(
        DeliveryDateCalculator,
        "get_next_delivery_date_for_product_type",
        autospec=True,
    )
    @patch.object(
        PickupLocationDeliveryChargeService,
        "get_delivery_charge_at_date",
        autospec=True,
    )
    def test_yearlyCharge_withoutPickupLocation_returnsZero(
        self, mock_get_charge, mock_get_next_date
    ):
        result = BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
            pickup_location_id=None,
            product_type=Mock(),
            growing_period=_build_growing_period(),
            cache={},
        )

        self.assertEqual(Decimal("0.00"), result)
        mock_get_next_date.assert_not_called()
        mock_get_charge.assert_not_called()

    @patch.object(
        DeliveryDateCalculator,
        "get_next_delivery_date_for_product_type",
        autospec=True,
    )
    @patch.object(
        PickupLocationDeliveryChargeService,
        "get_delivery_charge_at_date",
        autospec=True,
    )
    def test_yearlyCharge_sumsTheChargeOfEveryDelivery(
        self, mock_get_charge, mock_get_next_date
    ):
        mock_get_next_date.side_effect = [
            datetime.date(2026, 1, 5),
            datetime.date(2026, 1, 12),
            datetime.date(2026, 1, 19),
            datetime.date(2026, 1, 26),
            None,
        ]
        mock_get_charge.return_value = Decimal("2.50")

        result = BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
            pickup_location_id="location",
            product_type=Mock(),
            growing_period=_build_growing_period(),
            cache={},
        )

        self.assertEqual(Decimal("10.00"), result)
        self.assertEqual(4, mock_get_charge.call_count)

    @patch.object(
        DeliveryDateCalculator,
        "get_next_delivery_date_for_product_type",
        autospec=True,
    )
    @patch.object(
        PickupLocationDeliveryChargeService,
        "get_delivery_charge_at_date",
        autospec=True,
    )
    def test_yearlyCharge_usesTheChargeValidAtEachDeliveryDate(
        self, mock_get_charge, mock_get_next_date
    ):
        mock_get_next_date.side_effect = [
            datetime.date(2026, 1, 5),
            datetime.date(2026, 1, 12),
            None,
        ]
        mock_get_charge.side_effect = [Decimal("2.00"), Decimal("3.00")]

        result = BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
            pickup_location_id="location",
            product_type=Mock(),
            growing_period=_build_growing_period(),
            cache={},
        )

        self.assertEqual(Decimal("5.00"), result)

    @patch.object(
        DeliveryDateCalculator,
        "get_next_delivery_date_for_product_type",
        autospec=True,
    )
    @patch.object(
        PickupLocationDeliveryChargeService,
        "get_delivery_charge_at_date",
        autospec=True,
    )
    def test_yearlyCharge_withoutDeliveryInPeriod_returnsZero(
        self, mock_get_charge, mock_get_next_date
    ):
        mock_get_next_date.return_value = datetime.date(2026, 2, 2)

        result = BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
            pickup_location_id="location",
            product_type=Mock(),
            growing_period=_build_growing_period(),
            cache={},
        )

        self.assertEqual(Decimal("0.00"), result)
        mock_get_charge.assert_not_called()
