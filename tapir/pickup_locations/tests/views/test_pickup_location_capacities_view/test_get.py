from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.config import PICKING_MODE_BASKET, PICKING_MODE_SHARE
from tapir.pickup_locations.models import PickupLocationBasketCapacity
from tapir.wirgarten.constants import WEEKLY, ODD_WEEKS
from tapir.wirgarten.parameters import ParameterDefinitions, Parameter
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    PickupLocationCapabilityFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationCapacitiesViewGet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(key=Parameter.PICKING_BASKET_SIZES).update(
            value="small;medium;large"
        )

    def test_get_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)
        pickup_location = PickupLocationFactory.create()

        url = reverse("pickup_locations:pickup_location_capacities")
        response = self.client.get(f"{url}?pickup_location_id={pickup_location.id}")

        self.assertEqual(response.status_code, 403)

    def test_get_pickingModeIsBasket_returnsDataWithBasketSizeCapacities(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        pickup_location = PickupLocationFactory.create(name="test location name")
        TapirParameter.objects.filter(key=Parameter.PICKING_MODE).update(
            value=PICKING_MODE_BASKET
        )
        PickupLocationBasketCapacity.objects.create(
            pickup_location=pickup_location, basket_size_name="small", capacity=100
        )
        PickupLocationBasketCapacity.objects.create(
            pickup_location=pickup_location, basket_size_name="medium", capacity=75
        )

        url = reverse("pickup_locations:pickup_location_capacities")
        response = self.client.get(f"{url}?pickup_location_id={pickup_location.id}")

        self.assertEqual(response.status_code, 200)
        response_content = response.json()
        self.assertEqual(
            {
                "pickup_location_id": pickup_location.id,
                "pickup_location_name": "test location name",
                "picking_mode": PICKING_MODE_BASKET,
                "capacities_by_basket_size": [
                    {"basket_size_name": "small", "capacity": 100},
                    {"basket_size_name": "medium", "capacity": 75},
                    {"basket_size_name": "large", "capacity": None},
                ],
            },
            response_content,
        )

    def test_get_pickingModeIsShare_returnsDataWithShareCapacities(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        pickup_location = PickupLocationFactory.create(name="test location name")
        TapirParameter.objects.filter(key=Parameter.PICKING_MODE).update(
            value=PICKING_MODE_SHARE
        )
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
                "picking_mode": PICKING_MODE_SHARE,
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
