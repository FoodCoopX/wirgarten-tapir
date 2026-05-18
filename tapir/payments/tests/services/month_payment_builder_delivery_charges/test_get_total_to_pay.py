import datetime
from decimal import Decimal
from unittest.mock import patch, Mock

from tapir.payments.services.month_payment_builder_delivery_charges import (
    MonthPaymentBuilderDeliveryCharges,
)
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetTotalToPay(TapirUnitTest):
    def test_getTotalToPay_noSubscriptions_returnsZero(self):
        result = MonthPaymentBuilderDeliveryCharges.get_total_to_pay(
            range_start=datetime.date(year=2026, month=1, day=1),
            range_end=datetime.date(year=2026, month=2, day=1),
            contracts=[],
            cache={},
        )

        self.assertEqual(Decimal(0), result)

    @patch.object(
        PickupLocationDeliveryChargeService,
        "get_delivery_charge_at_date",
        autospec=True,
    )
    @patch.object(
        MemberPickupLocationGetter,
        "get_member_pickup_location_id_from_cache",
        autospec=True,
    )
    @patch.object(
        MonthPaymentBuilderDeliveryCharges,
        "get_billable_delivery_dates_in_range",
        autospec=True,
    )
    def test_getTotalToPay_threeBillableDates_returnsSumOfChargesAtEachDate(
        self,
        mock_get_billable_delivery_dates_in_range: Mock,
        mock_get_member_pickup_location_id_from_cache: Mock,
        mock_get_delivery_charge_at_date: Mock,
    ):
        delivery_dates = {
            datetime.date(year=2026, month=1, day=7),
            datetime.date(year=2026, month=1, day=14),
            datetime.date(year=2026, month=1, day=21),
        }
        mock_get_billable_delivery_dates_in_range.return_value = delivery_dates

        pickup_location_ids = {
            datetime.date(year=2026, month=1, day=7): "loc-A",
            datetime.date(year=2026, month=1, day=14): "loc-A",
            datetime.date(year=2026, month=1, day=21): "loc-B",
        }
        mock_get_member_pickup_location_id_from_cache.side_effect = (
            lambda member_id, reference_date, cache: pickup_location_ids[reference_date]
        )

        charges = {
            ("loc-A", datetime.date(year=2026, month=1, day=7)): Decimal("2.00"),
            ("loc-A", datetime.date(year=2026, month=1, day=14)): Decimal("2.00"),
            ("loc-B", datetime.date(year=2026, month=1, day=21)): Decimal("3.50"),
        }
        mock_get_delivery_charge_at_date.side_effect = (
            lambda pickup_location_id, reference_date, cache: charges[
                (pickup_location_id, reference_date)
            ]
        )

        subscription_mock = Mock(member_id="member-1")
        result = MonthPaymentBuilderDeliveryCharges.get_total_to_pay(
            range_start=datetime.date(year=2026, month=1, day=1),
            range_end=datetime.date(year=2026, month=2, day=1),
            contracts=[subscription_mock],
            cache={},
        )

        self.assertEqual(Decimal("7.50"), result)
