import datetime
from decimal import Decimal

from django.urls import reverse

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationDeliveryChargeFactory,
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

    def test_post_validData_createsNewEntry(self):
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
        entry = PickupLocationDeliveryCharge.objects.get(
            pickup_location=pickup_location
        )
        self.assertEqual(Decimal("2.50"), entry.amount)
        self.assertEqual(datetime.date(year=2026, month=6, day=1), entry.valid_from)

    def test_post_entryAlreadyExistsForValidFrom_updatesAmount(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        pickup_location = PickupLocationFactory.create()
        existing = PickupLocationDeliveryChargeFactory.create(
            pickup_location=pickup_location,
            amount=Decimal("1.00"),
            valid_from=datetime.date(year=2026, month=6, day=1),
        )

        url = reverse("pickup_locations:pickup_location_delivery_charges")
        response = self.client.post(
            url,
            data={
                "pickup_location_id": pickup_location.id,
                "amount": "3.00",
                "valid_from": "2026-06-01",
            },
        )

        self.assertEqual(response.status_code, 200)
        entries = list(
            PickupLocationDeliveryCharge.objects.filter(pickup_location=pickup_location)
        )
        self.assertEqual(1, len(entries))
        self.assertEqual(existing.id, entries[0].id)
        self.assertEqual(Decimal("3.00"), entries[0].amount)

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
