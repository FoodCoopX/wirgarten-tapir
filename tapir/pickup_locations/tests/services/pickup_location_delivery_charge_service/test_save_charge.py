import datetime
from decimal import Decimal

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.pickup_locations.tests.factories import (
    PickupLocationDeliveryChargeFactory,
)
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestSaveCharge(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        cls.pickup_location = PickupLocationFactory.create()
        cls.valid_from = datetime.date(year=2026, month=6, day=1)

    def test_saveCharge_noExistingEntry_createsNewEntry(self):
        PickupLocationDeliveryChargeService.save_charge(
            pickup_location=self.pickup_location,
            amount=Decimal("2.50"),
            valid_from=self.valid_from,
            cache={},
        )

        entries = list(
            PickupLocationDeliveryCharge.objects.filter(
                pickup_location=self.pickup_location
            )
        )
        self.assertEqual(1, len(entries))
        self.assertEqual(Decimal("2.50"), entries[0].amount)
        self.assertEqual(self.valid_from, entries[0].valid_from)

    def test_saveCharge_existingEntryWithSameValidFrom_updatesAmount(self):
        existing = PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location,
            amount=Decimal("1.00"),
            valid_from=self.valid_from,
        )

        PickupLocationDeliveryChargeService.save_charge(
            pickup_location=self.pickup_location,
            amount=Decimal("3.00"),
            valid_from=self.valid_from,
            cache={},
        )

        entries = list(
            PickupLocationDeliveryCharge.objects.filter(
                pickup_location=self.pickup_location
            )
        )
        self.assertEqual(1, len(entries))
        self.assertEqual(existing.id, entries[0].id)
        self.assertEqual(Decimal("3.00"), entries[0].amount)

    def test_saveCharge_existingEntryWithDifferentValidFrom_createsAnotherEntry(self):
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location,
            amount=Decimal("1.00"),
            valid_from=self.valid_from,
        )

        PickupLocationDeliveryChargeService.save_charge(
            pickup_location=self.pickup_location,
            amount=Decimal("3.00"),
            valid_from=self.valid_from + datetime.timedelta(days=30),
            cache={},
        )

        entries = list(
            PickupLocationDeliveryCharge.objects.filter(
                pickup_location=self.pickup_location
            ).order_by("valid_from")
        )
        self.assertEqual(2, len(entries))
        self.assertEqual(Decimal("1.00"), entries[0].amount)
        self.assertEqual(Decimal("3.00"), entries[1].amount)
