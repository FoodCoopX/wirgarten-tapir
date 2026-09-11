import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.test_utils import TapirUnitTest

REFERENCE_DATE = datetime.date(year=2026, month=5, day=15)


def _build_charge(
    amount: str, valid_from: datetime.date
) -> PickupLocationDeliveryCharge:
    return PickupLocationDeliveryCharge(
        pickup_location_id="test_location",
        amount=Decimal(amount),
        valid_from=valid_from,
    )


class TestGetDeliveryChargeAtDate(TapirUnitTest):
    @patch.object(
        TapirCache, "get_delivery_charges_by_pickup_location_id", autospec=True
    )
    def test_getDeliveryChargeAtDate_noChargeRowExists_returnsZero(
        self, mock_get_charges: Mock
    ):
        mock_get_charges.return_value = []
        cache = Mock()

        result = PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
            pickup_location_id="test_location",
            reference_date=REFERENCE_DATE,
            cache=cache,
        )

        self.assertEqual(Decimal("0.00"), result)
        mock_get_charges.assert_called_once_with(
            cache=cache, pickup_location_id="test_location"
        )

    @patch.object(
        TapirCache, "get_delivery_charges_by_pickup_location_id", autospec=True
    )
    def test_getDeliveryChargeAtDate_multipleEntries_returnsMostRecentValidEntry(
        self, mock_get_charges: Mock
    ):
        mock_get_charges.return_value = [
            _build_charge("1.50", REFERENCE_DATE - datetime.timedelta(days=60)),
            _build_charge("2.00", REFERENCE_DATE - datetime.timedelta(days=10)),
            _build_charge("3.00", REFERENCE_DATE + datetime.timedelta(days=10)),
        ]

        result = PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
            pickup_location_id="test_location",
            reference_date=REFERENCE_DATE,
            cache=Mock(),
        )

        self.assertEqual(Decimal("2.00"), result)

    @patch.object(
        TapirCache, "get_delivery_charges_by_pickup_location_id", autospec=True
    )
    def test_getDeliveryChargeAtDate_referenceBeforeAllEntries_returnsZero(
        self, mock_get_charges: Mock
    ):
        mock_get_charges.return_value = [
            _build_charge("2.00", REFERENCE_DATE + datetime.timedelta(days=10)),
        ]

        result = PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
            pickup_location_id="test_location",
            reference_date=REFERENCE_DATE,
            cache=Mock(),
        )

        self.assertEqual(Decimal("0.00"), result)

    @patch.object(
        TapirCache, "get_delivery_charges_by_pickup_location_id", autospec=True
    )
    def test_getDeliveryChargeAtDate_validFromEqualsReference_returnsThatAmount(
        self, mock_get_charges: Mock
    ):
        mock_get_charges.return_value = [_build_charge("4.50", REFERENCE_DATE)]

        result = PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
            pickup_location_id="test_location",
            reference_date=REFERENCE_DATE,
            cache=Mock(),
        )

        self.assertEqual(Decimal("4.50"), result)
