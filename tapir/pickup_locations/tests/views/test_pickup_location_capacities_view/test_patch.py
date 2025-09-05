from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.services.share_capacities_service import (
    SharesCapacityService,
)
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS, ODD_WEEKS
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    ProductTypeFactory,
    PickupLocationCapabilityFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationCapacitiesViewPatch(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.pickup_location = PickupLocationFactory.create()
        cls.product_type_1 = ProductTypeFactory.create(
            name="test product type 1", delivery_cycle=WEEKLY[0]
        )
        cls.product_type_2 = ProductTypeFactory.create(
            name="test product type 2", delivery_cycle=EVEN_WEEKS[0]
        )
        cls.product_type_3 = ProductTypeFactory.create(
            name="test product type 3", delivery_cycle=ODD_WEEKS[0]
        )
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_BASKET_SIZES).update(
            value="small;medium;large"
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=cls.pickup_location,
            product_type=cls.product_type_1,
            max_capacity=200,
        )

    def test_patch_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self.do_patch_call({})

        self.assertEqual(response.status_code, 403)

    @classmethod
    def build_post_data(
        cls,
    ):
        return {
            "pickup_location_id": cls.pickup_location.id,
            "pickup_location_name": "test location name",
            "capacities_by_shares": [
                {
                    "product_type_id": cls.product_type_1.id,
                    "product_type_name": "test product type 1",
                    "capacity": 100,
                },
                {
                    "product_type_id": cls.product_type_2.id,
                    "product_type_name": "test product type 2",
                    "capacity": 50,
                },
                {
                    "product_type_id": cls.product_type_3.id,
                    "product_type_name": "test product type 3",
                },
            ],
        }

    def do_patch_call(self, data):
        url = reverse("pickup_locations:pickup_location_capacities")
        response = self.client.patch(
            f"{url}?pickup_location_id={self.pickup_location.id}",
            data=data,
            content_type="application/json",
        )
        return response

    def test_patch_sendCorrectDataForPickingModeShare_capacitiesCorrectlyUpdated(
        self,
    ):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        data = self.build_post_data()
        response = self.do_patch_call(data)

        self.assertStatusCode(response, 200)
        result = SharesCapacityService.get_available_share_capacities_for_pickup_location_by_product_type(
            self.pickup_location
        )
        expected = {
            self.product_type_1: 100,
            self.product_type_2: 50,
            self.product_type_3: None,
        }
        self.assertEqual(expected, result)
