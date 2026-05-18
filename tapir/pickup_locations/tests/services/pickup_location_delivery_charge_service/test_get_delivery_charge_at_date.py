import datetime
from decimal import Decimal

from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.wirgarten.tests.factories import (
    PickupLocationFactory,
    PickupLocationDeliveryChargeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetDeliveryChargeAtDate(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        cls.pickup_location = PickupLocationFactory.create()
        cls.reference_date = datetime.date(year=2026, month=5, day=15)

    def test_getDeliveryChargeAtDate_noChargeRowExists_returnsZero(self):
        result = PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
            pickup_location_id=self.pickup_location.id,
            reference_date=self.reference_date,
            cache={},
        )

        self.assertEqual(Decimal("0.00"), result)

    def test_getDeliveryChargeAtDate_multipleEntries_returnsMostRecentValidEntry(
        self,
    ):
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location,
            amount=Decimal("1.50"),
            valid_from=self.reference_date - datetime.timedelta(days=60),
        )
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location,
            amount=Decimal("2.00"),
            valid_from=self.reference_date - datetime.timedelta(days=10),
        )
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location,
            amount=Decimal("3.00"),
            valid_from=self.reference_date + datetime.timedelta(days=10),
        )

        result = PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
            pickup_location_id=self.pickup_location.id,
            reference_date=self.reference_date,
            cache={},
        )

        self.assertEqual(Decimal("2.00"), result)

    def test_getDeliveryChargeAtDate_referenceBeforeAllEntries_returnsZero(self):
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location,
            amount=Decimal("2.00"),
            valid_from=self.reference_date + datetime.timedelta(days=10),
        )

        result = PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
            pickup_location_id=self.pickup_location.id,
            reference_date=self.reference_date,
            cache={},
        )

        self.assertEqual(Decimal("0.00"), result)

    def test_getDeliveryChargeAtDate_validFromEqualsReference_returnsThatAmount(self):
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location,
            amount=Decimal("4.50"),
            valid_from=self.reference_date,
        )

        result = PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
            pickup_location_id=self.pickup_location.id,
            reference_date=self.reference_date,
            cache={},
        )

        self.assertEqual(Decimal("4.50"), result)

    def test_getDeliveryChargeAtDate_otherLocationHasCharge_returnsZeroForRequestedLocation(
        self,
    ):
        other_location = PickupLocationFactory.create()
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=other_location,
            amount=Decimal("5.00"),
            valid_from=self.reference_date - datetime.timedelta(days=10),
        )

        result = PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
            pickup_location_id=self.pickup_location.id,
            reference_date=self.reference_date,
            cache={},
        )

        self.assertEqual(Decimal("0.00"), result)
