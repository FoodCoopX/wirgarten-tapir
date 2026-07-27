import datetime
from decimal import Decimal

from django.urls import reverse

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.pickup_locations.tests.factories import (
    PickupLocationDeliveryChargeFactory,
)
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationDeliveryChargesViewGet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalMember_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)
        pickup_location = PickupLocationFactory.create()

        url = reverse("pickup_locations:pickup_location_delivery_charges")
        response = self.client.get(f"{url}?pickup_location_id={pickup_location.id}")

        self.assertEqual(response.status_code, 403)

    def test_get_withEntries_returnsEntriesSortedByValidFromDescending(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        pickup_location = PickupLocationFactory.create(name="Test Location")

        older = PickupLocationDeliveryChargeFactory.create(
            pickup_location=pickup_location,
            amount=Decimal("1.50"),
            valid_from=datetime.date(year=2026, month=1, day=1),
        )
        newer = PickupLocationDeliveryChargeFactory.create(
            pickup_location=pickup_location,
            amount=Decimal("2.00"),
            valid_from=datetime.date(year=2026, month=4, day=1),
        )

        url = reverse("pickup_locations:pickup_location_delivery_charges")
        response = self.client.get(f"{url}?pickup_location_id={pickup_location.id}")

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(pickup_location.id, content["pickup_location_id"])
        self.assertEqual("Test Location", content["pickup_location_name"])
        self.assertEqual(
            [
                {
                    "id": newer.id,
                    "amount": "2.00",
                    "valid_from": "2026-04-01",
                },
                {
                    "id": older.id,
                    "amount": "1.50",
                    "valid_from": "2026-01-01",
                },
            ],
            content["entries"],
        )

    def test_get_noEntries_returnsEmptyList(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        pickup_location = PickupLocationFactory.create(name="Empty Location")

        url = reverse("pickup_locations:pickup_location_delivery_charges")
        response = self.client.get(f"{url}?pickup_location_id={pickup_location.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([], response.json()["entries"])
