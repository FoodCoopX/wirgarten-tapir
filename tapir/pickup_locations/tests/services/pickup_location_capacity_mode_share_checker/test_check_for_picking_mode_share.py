from unittest.mock import patch, Mock, call

from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.tests.factories import (
    PickupLocationFactory,
    PickupLocationCapabilityFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCheckForPickingModeShare(TapirIntegrationTest):

    @patch.object(
        PickupLocationCapacityModeShareChecker,
        "check_capacity_for_product_type",
        autospec=True,
    )
    def test_checkForPickingModeShare_capacityIsUnlimitedForSomeSizes_checkCapacityOnlyForProductTypesWithLimitedCapacity(
        self, mock_check_capacity_for_product_type: Mock
    ):
        pickup_location = PickupLocationFactory.create()
        product_type_1 = ProductTypeFactory.create(delivery_cycle=WEEKLY[0])
        PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location,
            max_capacity=10,
            product_type=product_type_1,
        )
        product_type_2 = ProductTypeFactory.create(delivery_cycle=WEEKLY[0])
        PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location,
            max_capacity=None,
            product_type=product_type_2,
        )
        ordered_product_to_quantity_map = Mock()
        already_registered_member = Mock()
        subscription_start = Mock()

        mock_check_capacity_for_product_type.return_value = True

        cache = {}

        result = PickupLocationCapacityModeShareChecker.check_for_picking_mode_share(
            pickup_location=pickup_location,
            order=ordered_product_to_quantity_map,
            already_registered_member=already_registered_member,
            subscription_start=subscription_start,
            cache=cache,
        )

        self.assertTrue(result)

        mock_check_capacity_for_product_type.assert_called_once_with(
            product_type=product_type_1,
            member=already_registered_member,
            pickup_location=pickup_location,
            subscription_start=subscription_start,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            check_waiting_list_entries=True,
            cache=cache,
        )

    @patch.object(
        PickupLocationCapacityModeShareChecker, "check_capacity_for_product_type"
    )
    def test_checkForPickingModeShare_oneCapacityCheckFails_returnsFalse(
        self, mock_check_capacity_for_product_type: Mock
    ):
        pickup_location = PickupLocationFactory.create()
        product_type_1 = ProductTypeFactory.create(delivery_cycle=WEEKLY[0])
        PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location,
            max_capacity=10,
            product_type=product_type_1,
        )
        product_type_2 = ProductTypeFactory.create(delivery_cycle=WEEKLY[0])
        PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location,
            max_capacity=15,
            product_type=product_type_2,
        )
        ordered_product_to_quantity_map = Mock()
        already_registered_member = Mock()
        subscription_start = Mock()

        mock_check_capacity_for_product_type.side_effect = [True, False]

        cache = {}

        result = PickupLocationCapacityModeShareChecker.check_for_picking_mode_share(
            pickup_location=pickup_location,
            order=ordered_product_to_quantity_map,
            already_registered_member=already_registered_member,
            subscription_start=subscription_start,
            cache=cache,
        )

        self.assertFalse(result)
        self.assertEqual(2, mock_check_capacity_for_product_type.call_count)
        mock_check_capacity_for_product_type.assert_has_calls(
            [
                call(
                    product_type=product_type_1,
                    member=already_registered_member,
                    pickup_location=pickup_location,
                    subscription_start=subscription_start,
                    ordered_product_to_quantity_map=ordered_product_to_quantity_map,
                    check_waiting_list_entries=True,
                    cache=cache,
                ),
                call(
                    product_type=product_type_2,
                    member=already_registered_member,
                    pickup_location=pickup_location,
                    subscription_start=subscription_start,
                    ordered_product_to_quantity_map=ordered_product_to_quantity_map,
                    check_waiting_list_entries=True,
                    cache=cache,
                ),
            ],
            any_order=True,
        )
