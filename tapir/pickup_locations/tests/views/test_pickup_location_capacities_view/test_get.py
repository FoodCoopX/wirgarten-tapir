from django.urls import reverse

from tapir.wirgarten.constants import WEEKLY, ODD_WEEKS
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    PickupLocationCapabilityFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationCapacitiesViewGet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)
        pickup_location = PickupLocationFactory.create()

        url = reverse("pickup_locations:pickup_location_capacities")
        response = self.client.get(f"{url}?pickup_location_id={pickup_location.id}")

        self.assertEqual(response.status_code, 403)

    def test_get_pickingModeIsShare_returnsDataWithShareCapacities(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        pickup_location = PickupLocationFactory.create(name="test location name")

        capability_1 = PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location,
            product_type__name="test product type 1",
            product_type__delivery_cycle=WEEKLY[0],
            max_capacity=100,
        )
        capability_2 = PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location,
            product_type__name="test product type 2",
            product_type__delivery_cycle=ODD_WEEKS[0],
            max_capacity=50,
        )

        url = reverse("pickup_locations:pickup_location_capacities")
        response = self.client.get(f"{url}?pickup_location_id={pickup_location.id}")

        self.assertEqual(response.status_code, 200)
        response_content = response.json()
        self.assertEqual(
            {
                "pickup_location_id": pickup_location.id,
                "pickup_location_name": "test location name",
                "capacities_by_shares": [
                    {
                        "product_type_id": capability_1.product_type.id,
                        "product_type_name": "test product type 1",
                        "capacity": 100,
                    },
                    {
                        "product_type_id": capability_2.product_type.id,
                        "product_type_name": "test product type 2",
                        "capacity": 50,
                    },
                ],
            },
            response_content,
        )
