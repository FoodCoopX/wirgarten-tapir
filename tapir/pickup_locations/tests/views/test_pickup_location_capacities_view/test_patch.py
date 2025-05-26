from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.config import PICKING_MODE_SHARE, PICKING_MODE_BASKET
from tapir.pickup_locations.models import PickupLocationBasketCapacity
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
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
        ParameterDefinitions().import_definitions()
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
        PickupLocationBasketCapacity.objects.create(
            pickup_location=cls.pickup_location, basket_size_name="small", capacity=None
        )
        PickupLocationBasketCapacity.objects.create(
            pickup_location=cls.pickup_location, basket_size_name="medium", capacity=150
        )

    def test_patch_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self.do_patch_call({})

        self.assertEqual(response.status_code, 403)

    @classmethod
    def build_post_data(
        cls,
        mode_field_value: str,
        include_capacities_by_share: bool,
        include_capacities_by_basket_size: bool,
    ):
        data = {
            "pickup_location_id": cls.pickup_location.id,
            "pickup_location_name": "test location name",
            "picking_mode": mode_field_value,
        }

        if include_capacities_by_share:
            data["capacities_by_shares"] = [
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
            ]

        if include_capacities_by_basket_size:
            data["capacities_by_basket_size"] = [
                {"basket_size_name": "small", "capacity": 100},
                {"basket_size_name": "medium", "capacity": 75},
                {"basket_size_name": "large"},
            ]

        return data

    def do_patch_call(self, data):
        url = reverse("pickup_locations:pickup_location_capacities")
        response = self.client.patch(
            f"{url}?pickup_location_id={self.pickup_location.id}",
            data=data,
            content_type="application/json",
        )
        return response

    def test_patch_sendPickingModeDifferentFromSettings_returnsError(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=PICKING_MODE_BASKET
        )

        data = self.build_post_data(PICKING_MODE_SHARE, True, False)
        response = self.do_patch_call(data)

        self.assertStatusCode(response, 400)

    def test_patch_sendDataForPickingModeBasketButSettingsIsModeShare_returnsError(
        self,
    ):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=PICKING_MODE_SHARE
        )

        data = self.build_post_data(PICKING_MODE_SHARE, False, True)
        response = self.do_patch_call(data)

        self.assertStatusCode(response, 400)

    def test_patch_sendDataForPickingModeSharesButSettingsIsModeBasket_returnsError(
        self,
    ):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=PICKING_MODE_BASKET
        )

        data = self.build_post_data(PICKING_MODE_BASKET, True, False)
        response = self.do_patch_call(data)

        self.assertStatusCode(response, 400)

    def test_patch_sendCorrectDataForPickingModeBasket_capacitiesCorrectlyUpdated(
        self,
    ):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=PICKING_MODE_BASKET
        )

        data = self.build_post_data(PICKING_MODE_BASKET, False, True)
        response = self.do_patch_call(data)

        self.assertStatusCode(response, 200)
        result = (
            BasketSizeCapacitiesService.get_basket_size_capacities_for_pickup_location(
                self.pickup_location, cache={}
            )
        )
        self.assertEqual({"small": 100, "medium": 75, "large": None}, result)

    def test_patch_sendCorrectDataForPickingModeShare_capacitiesCorrectlyUpdated(
        self,
    ):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=PICKING_MODE_SHARE
        )

        data = self.build_post_data(PICKING_MODE_SHARE, True, False)
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
