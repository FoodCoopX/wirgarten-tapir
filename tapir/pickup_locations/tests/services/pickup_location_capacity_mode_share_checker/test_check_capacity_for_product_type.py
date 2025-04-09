from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)


class TestCheckCapacityForProductType(SimpleTestCase):
    @patch.object(
        PickupLocationCapacityModeShareChecker,
        "calculate_capacity_used_by_the_ordered_products",
    )
    @patch.object(
        PickupLocationCapacityModeShareChecker,
        "get_capacity_used_by_member_before_changes",
    )
    @patch.object(PickupLocationCapacityModeShareChecker, "get_free_capacity_at_date")
    def test_checkCapacityForProductType_newUsageIsOverCapacity_returnsFalse(
        self,
        mock_get_free_capacity_at_date: Mock,
        mock_get_capacity_used_by_member_before_changes: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
    ):
        mock_get_free_capacity_at_date.return_value = 1
        mock_get_capacity_used_by_member_before_changes.return_value = 2
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 4
        member = Mock()
        pickup_location = Mock()
        subscription_start = Mock()
        ordered_product_to_quantity_map = Mock()
        product_type = Mock()
        cache = {}

        result = PickupLocationCapacityModeShareChecker.check_capacity_for_product_type(
            product_type=product_type,
            member=member,
            pickup_location=pickup_location,
            subscription_start=subscription_start,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            cache=cache,
        )

        self.assertFalse(result)

        mock_get_free_capacity_at_date.assert_called_once_with(
            pickup_location=pickup_location,
            product_type=product_type,
            reference_date=subscription_start,
            cache=cache,
        )
        mock_get_capacity_used_by_member_before_changes.assert_called_once_with(
            member=member,
            subscription_start=subscription_start,
            product_type=product_type,
            cache=cache,
        )
        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            product_type=product_type,
            reference_date=subscription_start,
            cache=cache,
        )

    @patch.object(
        PickupLocationCapacityModeShareChecker,
        "calculate_capacity_used_by_the_ordered_products",
    )
    @patch.object(
        PickupLocationCapacityModeShareChecker,
        "get_capacity_used_by_member_before_changes",
    )
    @patch.object(PickupLocationCapacityModeShareChecker, "get_free_capacity_at_date")
    def test_checkCapacityForProductType_newUsageIsEqualToCapacity_returnsTrue(
        self,
        mock_get_free_capacity_at_date: Mock,
        mock_get_capacity_used_by_member_before_changes: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
    ):
        mock_get_free_capacity_at_date.return_value = 1
        mock_get_capacity_used_by_member_before_changes.return_value = 2
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 3
        member = Mock()
        pickup_location = Mock()
        subscription_start = Mock()
        ordered_product_to_quantity_map = Mock()
        product_type = Mock()
        cache = {}

        result = PickupLocationCapacityModeShareChecker.check_capacity_for_product_type(
            product_type=product_type,
            member=member,
            pickup_location=pickup_location,
            subscription_start=subscription_start,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            cache=cache,
        )

        self.assertTrue(result)

        mock_get_free_capacity_at_date.assert_called_once_with(
            pickup_location=pickup_location,
            product_type=product_type,
            reference_date=subscription_start,
            cache=cache,
        )
        mock_get_capacity_used_by_member_before_changes.assert_called_once_with(
            member=member,
            subscription_start=subscription_start,
            product_type=product_type,
            cache=cache,
        )
        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            product_type=product_type,
            reference_date=subscription_start,
            cache=cache,
        )

    @patch.object(
        PickupLocationCapacityModeShareChecker,
        "calculate_capacity_used_by_the_ordered_products",
    )
    @patch.object(
        PickupLocationCapacityModeShareChecker,
        "get_capacity_used_by_member_before_changes",
    )
    @patch.object(PickupLocationCapacityModeShareChecker, "get_free_capacity_at_date")
    def test_checkCapacityForProductType_newUsageIsBelowCapacity_returnsTrue(
        self,
        mock_get_free_capacity_at_date: Mock,
        mock_get_capacity_used_by_member_before_changes: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
    ):
        mock_get_free_capacity_at_date.return_value = 2
        mock_get_capacity_used_by_member_before_changes.return_value = 0
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 1
        member = Mock()
        pickup_location = Mock()
        subscription_start = Mock()
        ordered_product_to_quantity_map = Mock()
        product_type = Mock()
        cache = {}

        result = PickupLocationCapacityModeShareChecker.check_capacity_for_product_type(
            product_type=product_type,
            member=member,
            pickup_location=pickup_location,
            subscription_start=subscription_start,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            cache=cache,
        )

        self.assertTrue(result)

        mock_get_free_capacity_at_date.assert_called_once_with(
            pickup_location=pickup_location,
            product_type=product_type,
            reference_date=subscription_start,
            cache=cache,
        )
        mock_get_capacity_used_by_member_before_changes.assert_called_once_with(
            member=member,
            subscription_start=subscription_start,
            product_type=product_type,
            cache=cache,
        )
        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            product_type=product_type,
            reference_date=subscription_start,
            cache=cache,
        )
