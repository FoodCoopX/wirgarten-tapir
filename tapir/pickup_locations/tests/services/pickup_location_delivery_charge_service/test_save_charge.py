import datetime
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.pickup_locations.tests.factories import (
    PickupLocationDeliveryChargeFactory,
)
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch(
    "tapir.pickup_locations.services.pickup_location_delivery_charge_service.get_today"
)
class TestSaveCharge(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        cls.pickup_location = PickupLocationFactory.create()
        cls.today = datetime.date(year=2026, month=1, day=1)
        cls.valid_from = datetime.date(year=2026, month=6, day=1)

    def test_saveCharge_noExistingEntry_createsNewEntry(self, mock_get_today):
        mock_get_today.return_value = self.today

        PickupLocationDeliveryChargeService.save_charge(
            pickup_location=self.pickup_location,
            amount=Decimal("2.50"),
            valid_from=self.valid_from,
            cache={},
        )

        entries = list(PickupLocationDeliveryCharge.objects.all())
        self.assertEqual(1, len(entries))
        self.assertEqual(self.pickup_location, entries[0].pickup_location)
        self.assertEqual(Decimal("2.50"), entries[0].amount)
        self.assertEqual(self.valid_from, entries[0].valid_from)

    def test_saveCharge_existingEntryWithSameValidFrom_updatesAmount(
        self, mock_get_today
    ):
        mock_get_today.return_value = self.today
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

        entries = list(PickupLocationDeliveryCharge.objects.all())
        self.assertEqual(1, len(entries))
        self.assertEqual(self.pickup_location, entries[0].pickup_location)
        self.assertEqual(existing.id, entries[0].id)
        self.assertEqual(Decimal("3.00"), entries[0].amount)

    def test_saveCharge_existingEntryWithDifferentValidFrom_createsAnotherEntry(
        self, mock_get_today
    ):
        mock_get_today.return_value = self.today
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
            PickupLocationDeliveryCharge.objects.all().order_by("valid_from")
        )
        self.assertEqual(2, len(entries))
        self.assertEqual(self.pickup_location, entries[0].pickup_location)
        self.assertEqual(self.pickup_location, entries[1].pickup_location)
        self.assertEqual(Decimal("1.00"), entries[0].amount)
        self.assertEqual(Decimal("3.00"), entries[1].amount)

    def test_saveCharge_validFromInThePast_raisesValidationError(self, mock_get_today):
        mock_get_today.return_value = self.valid_from

        with self.assertRaises(ValidationError):
            PickupLocationDeliveryChargeService.save_charge(
                pickup_location=self.pickup_location,
                amount=Decimal("2.50"),
                valid_from=self.valid_from - datetime.timedelta(days=1),
                cache={},
            )

        self.assertFalse(PickupLocationDeliveryCharge.objects.exists())

    def test_saveCharge_validFromIsToday_raisesValidationError(self, mock_get_today):
        mock_get_today.return_value = self.valid_from

        with self.assertRaises(ValidationError):
            PickupLocationDeliveryChargeService.save_charge(
                pickup_location=self.pickup_location,
                amount=Decimal("2.50"),
                valid_from=self.valid_from,
                cache={},
            )

        self.assertFalse(PickupLocationDeliveryCharge.objects.exists())
