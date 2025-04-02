from unittest.mock import patch, Mock, call

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.models import PickupLocationBasketCapacity
from tapir.pickup_locations.services.pickup_location_capacity_mode_basket_checker import (
    PickupLocationCapacityModeBasketChecker,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCheckForPickingModeBasket(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_BASKET_SIZES).update(
            value="small;medium"
        )

    @patch.object(
        PickupLocationCapacityModeBasketChecker, "check_capacity_for_basket_size"
    )
    def test_checkForPickingModeBasket_capacityIsUnlimitedForSomeSizes_checkCapacityOnlyForSizesWithLimitedCapacity(
        self, mock_check_capacity_for_basket_size: Mock
    ):
        pickup_location = PickupLocationFactory()
        PickupLocationBasketCapacity.objects.create(
            pickup_location=pickup_location, basket_size_name="small", capacity=10
        )
        PickupLocationBasketCapacity.objects.create(
            pickup_location=pickup_location, basket_size_name="medium", capacity=None
        )
        ordered_product_to_quantity_map = Mock()
        already_registered_member = Mock()
        subscription_start = Mock()

        mock_check_capacity_for_basket_size.return_value = True

        result = PickupLocationCapacityModeBasketChecker.check_for_picking_mode_basket(
            pickup_location=pickup_location,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            already_registered_member=already_registered_member,
            subscription_start=subscription_start,
        )

        self.assertTrue(result)

        mock_check_capacity_for_basket_size.assert_called_once_with(
            basket_size="small",
            available_capacity=10,
            member=already_registered_member,
            pickup_location=pickup_location,
            subscription_start=subscription_start,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
        )

    @patch.object(
        PickupLocationCapacityModeBasketChecker, "check_capacity_for_basket_size"
    )
    def test_checkForPickingModeBasket_oneCapacityCheckFails_returnsFalse(
        self, mock_check_capacity_for_basket_size: Mock
    ):
        pickup_location = PickupLocationFactory()
        PickupLocationBasketCapacity.objects.create(
            pickup_location=pickup_location, basket_size_name="small", capacity=10
        )
        PickupLocationBasketCapacity.objects.create(
            pickup_location=pickup_location, basket_size_name="medium", capacity=20
        )
        ordered_product_to_quantity_map = Mock()
        already_registered_member = Mock()
        subscription_start = Mock()

        mock_check_capacity_for_basket_size.side_effect = [True, False]

        result = PickupLocationCapacityModeBasketChecker.check_for_picking_mode_basket(
            pickup_location=pickup_location,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            already_registered_member=already_registered_member,
            subscription_start=subscription_start,
        )

        self.assertFalse(result)

        self.assertEqual(2, mock_check_capacity_for_basket_size.call_count)
        mock_check_capacity_for_basket_size.assert_has_calls(
            [
                call(
                    basket_size="small",
                    available_capacity=10,
                    member=already_registered_member,
                    pickup_location=pickup_location,
                    subscription_start=subscription_start,
                    ordered_product_to_quantity_map=ordered_product_to_quantity_map,
                ),
                call(
                    basket_size="medium",
                    available_capacity=20,
                    member=already_registered_member,
                    pickup_location=pickup_location,
                    subscription_start=subscription_start,
                    ordered_product_to_quantity_map=ordered_product_to_quantity_map,
                ),
            ],
            any_order=True,
        )
