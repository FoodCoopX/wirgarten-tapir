import datetime
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.pickup_locations.tests.factories import (
    PickupLocationDeliveryChargeFactory,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch(
    "tapir.pickup_locations.services.pickup_location_delivery_charge_service.get_today"
)
class TestPickupLocationDeliveryChargesViewDelete(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.today = datetime.date(year=2026, month=6, day=1)

    def test_delete_loggedInAsNormalMember_returns403(self, mock_get_today):
        mock_get_today.return_value = self.today
        member = MemberFactory.create()
        self.client.force_login(member)
        charge = PickupLocationDeliveryChargeFactory.create(
            valid_from=self.today + datetime.timedelta(days=1)
        )

        url = reverse("pickup_locations:pickup_location_delivery_charges")
        response = self.client.delete(f"{url}?id={charge.id}")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            PickupLocationDeliveryCharge.objects.filter(id=charge.id).exists()
        )

    def test_delete_futureEntry_returns200AndDeletesEntry(self, mock_get_today):
        mock_get_today.return_value = self.today
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        pickup_location = PickupLocationFactory.create()
        charge = PickupLocationDeliveryChargeFactory.create(
            pickup_location=pickup_location,
            amount=Decimal("2.50"),
            valid_from=self.today + datetime.timedelta(days=1),
        )

        url = reverse("pickup_locations:pickup_location_delivery_charges")
        response = self.client.delete(f"{url}?id={charge.id}")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            PickupLocationDeliveryCharge.objects.filter(id=charge.id).exists()
        )

    def test_delete_pastEntry_returns400(self, mock_get_today):
        mock_get_today.return_value = self.today
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        charge = PickupLocationDeliveryChargeFactory.create(
            valid_from=self.today - datetime.timedelta(days=1)
        )

        url = reverse("pickup_locations:pickup_location_delivery_charges")
        response = self.client.delete(f"{url}?id={charge.id}")

        self.assertEqual(response.status_code, 400)
        self.assertTrue(
            PickupLocationDeliveryCharge.objects.filter(id=charge.id).exists()
        )

    def test_delete_unknownId_returns404(self, mock_get_today):
        mock_get_today.return_value = self.today
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        url = reverse("pickup_locations:pickup_location_delivery_charges")
        response = self.client.delete(f"{url}?id=unknown-id")

        self.assertEqual(response.status_code, 404)
