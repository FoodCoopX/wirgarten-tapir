import datetime
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationDeliveryChargesViewPost(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_loggedInAsNormalMember_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)
        pickup_location = PickupLocationFactory.create()

        url = reverse("pickup_locations:pickup_location_delivery_charges")
        response = self.client.post(
            url,
            data={
                "pickup_location_id": pickup_location.id,
                "amount": "2.50",
                "valid_from": "2026-06-01",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(PickupLocationDeliveryCharge.objects.exists())

    @patch.object(PickupLocationDeliveryChargeService, "save_charge", autospec=True)
    def test_post_validData_forwardsToService(self, mock_save_charge):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        pickup_location = PickupLocationFactory.create()

        url = reverse("pickup_locations:pickup_location_delivery_charges")
        response = self.client.post(
            url,
            data={
                "pickup_location_id": pickup_location.id,
                "amount": "2.50",
                "valid_from": "2026-06-01",
            },
        )

        self.assertEqual(response.status_code, 200)
        mock_save_charge.assert_called_once_with(
            pickup_location=pickup_location,
            amount=Decimal("2.50"),
            valid_from=datetime.date(year=2026, month=6, day=1),
            cache={},
        )

    def test_post_negativeAmount_returns400(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        pickup_location = PickupLocationFactory.create()

        url = reverse("pickup_locations:pickup_location_delivery_charges")
        response = self.client.post(
            url,
            data={
                "pickup_location_id": pickup_location.id,
                "amount": "-1.00",
                "valid_from": "2026-06-01",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PickupLocationDeliveryCharge.objects.exists())

    @patch(
        "tapir.pickup_locations.services.pickup_location_delivery_charge_service.get_today"
    )
    def test_post_validFromInThePast_returns400(self, mock_get_today):
        mock_get_today.return_value = datetime.date(year=2026, month=6, day=1)
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        pickup_location = PickupLocationFactory.create()

        url = reverse("pickup_locations:pickup_location_delivery_charges")
        response = self.client.post(
            url,
            data={
                "pickup_location_id": pickup_location.id,
                "amount": "2.50",
                "valid_from": "2026-05-01",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PickupLocationDeliveryCharge.objects.exists())
