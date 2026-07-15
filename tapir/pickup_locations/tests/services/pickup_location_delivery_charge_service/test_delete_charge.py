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
class TestDeleteCharge(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        cls.pickup_location = PickupLocationFactory.create()
        cls.today = datetime.date(year=2026, month=6, day=1)

    def test_deleteCharge_futureEntry_deletesEntry(self, mock_get_today):
        mock_get_today.return_value = self.today
        charge = PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location,
            amount=Decimal("2.50"),
            valid_from=self.today + datetime.timedelta(days=1),
        )

        PickupLocationDeliveryChargeService.delete_charge(charge_id=charge.id, cache={})

        self.assertFalse(
            PickupLocationDeliveryCharge.objects.filter(id=charge.id).exists()
        )

    def test_deleteCharge_pastEntry_raisesValidationError(self, mock_get_today):
        mock_get_today.return_value = self.today
        charge = PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location,
            amount=Decimal("2.50"),
            valid_from=self.today - datetime.timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            PickupLocationDeliveryChargeService.delete_charge(
                charge_id=charge.id, cache={}
            )

        self.assertTrue(
            PickupLocationDeliveryCharge.objects.filter(id=charge.id).exists()
        )

    def test_deleteCharge_entryValidFromIsToday_raisesValidationError(
        self, mock_get_today
    ):
        mock_get_today.return_value = self.today
        charge = PickupLocationDeliveryChargeFactory.create(
            pickup_location=self.pickup_location,
            amount=Decimal("2.50"),
            valid_from=self.today,
        )

        with self.assertRaises(ValidationError):
            PickupLocationDeliveryChargeService.delete_charge(
                charge_id=charge.id, cache={}
            )

        self.assertTrue(
            PickupLocationDeliveryCharge.objects.filter(id=charge.id).exists()
        )

    def test_deleteCharge_unknownId_raisesDoesNotExist(self, mock_get_today):
        mock_get_today.return_value = self.today

        with self.assertRaises(PickupLocationDeliveryCharge.DoesNotExist):
            PickupLocationDeliveryChargeService.delete_charge(
                charge_id="unknown-id", cache={}
            )
