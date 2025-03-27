from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.pickup_locations.services.pickup_location_capacity_mode_basket_checker import (
    PickupLocationCapacityModeBasketChecker,
)


class TestCheckCapacityForBasketSize(SimpleTestCase):
    @patch.object(
        PickupLocationCapacityModeBasketChecker,
        "calculate_capacity_used_by_the_ordered_products",
    )
    @patch.object(
        PickupLocationCapacityModeBasketChecker,
        "get_capacity_used_by_member_before_changes",
    )
    @patch.object(PickupLocationCapacityModeBasketChecker, "get_current_capacity_usage")
    def test_checkCapacityForBasketSize_newUsageIsOverCapacity_returnsFalse(
        self,
        mock_get_current_capacity_usage: Mock,
        mock_get_capacity_used_by_member_before_changes: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
    ):
        mock_get_current_capacity_usage.return_value = 10
        mock_get_capacity_used_by_member_before_changes.return_value = 2
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 4
        member = Mock()
        pickup_location = Mock()
        subscription_start = Mock()
        ordered_product_to_quantity_map = Mock()

        result = PickupLocationCapacityModeBasketChecker.check_capacity_for_basket_size(
            basket_size="test_size",
            available_capacity=11,
            member=member,
            pickup_location=pickup_location,
            subscription_start=subscription_start,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
        )

        self.assertFalse(result)

        mock_get_current_capacity_usage.assert_called_once_with(
            pickup_location=pickup_location,
            basket_size="test_size",
            subscription_start=subscription_start,
        )
        mock_get_capacity_used_by_member_before_changes.assert_called_once_with(
            member=member,
            subscription_start=subscription_start,
            basket_size="test_size",
        )
        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            basket_size="test_size",
        )

    @patch.object(
        PickupLocationCapacityModeBasketChecker,
        "calculate_capacity_used_by_the_ordered_products",
    )
    @patch.object(
        PickupLocationCapacityModeBasketChecker,
        "get_capacity_used_by_member_before_changes",
    )
    @patch.object(PickupLocationCapacityModeBasketChecker, "get_current_capacity_usage")
    def test_checkCapacityForBasketSize_newUsageIsEqualToCapacity_returnsTrue(
        self,
        mock_get_current_capacity_usage: Mock,
        mock_get_capacity_used_by_member_before_changes: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
    ):
        mock_get_current_capacity_usage.return_value = 10
        mock_get_capacity_used_by_member_before_changes.return_value = 2
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 3
        member = Mock()
        pickup_location = Mock()
        subscription_start = Mock()
        ordered_product_to_quantity_map = Mock()

        result = PickupLocationCapacityModeBasketChecker.check_capacity_for_basket_size(
            basket_size="test_size",
            available_capacity=11,
            member=member,
            pickup_location=pickup_location,
            subscription_start=subscription_start,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
        )

        self.assertTrue(result)

        mock_get_current_capacity_usage.assert_called_once_with(
            pickup_location=pickup_location,
            basket_size="test_size",
            subscription_start=subscription_start,
        )
        mock_get_capacity_used_by_member_before_changes.assert_called_once_with(
            member=member,
            subscription_start=subscription_start,
            basket_size="test_size",
        )
        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            basket_size="test_size",
        )

    @patch.object(
        PickupLocationCapacityModeBasketChecker,
        "calculate_capacity_used_by_the_ordered_products",
    )
    @patch.object(
        PickupLocationCapacityModeBasketChecker,
        "get_capacity_used_by_member_before_changes",
    )
    @patch.object(PickupLocationCapacityModeBasketChecker, "get_current_capacity_usage")
    def test_checkCapacityForBasketSize_newUsageIsBelowCapacity_returnsTrue(
        self,
        mock_get_current_capacity_usage: Mock,
        mock_get_capacity_used_by_member_before_changes: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
    ):
        mock_get_current_capacity_usage.return_value = 10
        mock_get_capacity_used_by_member_before_changes.return_value = 0
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 1
        member = Mock()
        pickup_location = Mock()
        subscription_start = Mock()
        ordered_product_to_quantity_map = Mock()

        result = PickupLocationCapacityModeBasketChecker.check_capacity_for_basket_size(
            basket_size="test_size",
            available_capacity=11,
            member=member,
            pickup_location=pickup_location,
            subscription_start=subscription_start,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
        )

        self.assertTrue(result)

        mock_get_current_capacity_usage.assert_called_once_with(
            pickup_location=pickup_location,
            basket_size="test_size",
            subscription_start=subscription_start,
        )
        mock_get_capacity_used_by_member_before_changes.assert_called_once_with(
            member=member,
            subscription_start=subscription_start,
            basket_size="test_size",
        )
        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            basket_size="test_size",
        )
