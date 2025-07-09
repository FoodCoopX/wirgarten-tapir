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
    @patch.object(PickupLocationCapacityModeBasketChecker, "get_free_capacity_at_date")
    def test_checkCapacityForBasketSize_newUsageIsOverCapacity_returnsFalse(
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
        cache = {}

        result = PickupLocationCapacityModeBasketChecker.check_capacity_for_basket_size(
            basket_size="test_size",
            member=member,
            pickup_location=pickup_location,
            subscription_start=subscription_start,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            cache=cache,
        )

        self.assertFalse(result)

        mock_get_free_capacity_at_date.assert_called_once_with(
            pickup_location=pickup_location,
            basket_size="test_size",
            reference_date=subscription_start,
            cache=cache,
        )
        mock_get_capacity_used_by_member_before_changes.assert_called_once_with(
            member=member,
            subscription_start=subscription_start,
            basket_size="test_size",
            cache=cache,
        )
        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            basket_size="test_size",
            cache=cache,
        )

    @patch.object(
        PickupLocationCapacityModeBasketChecker,
        "calculate_capacity_used_by_the_ordered_products",
    )
    @patch.object(
        PickupLocationCapacityModeBasketChecker,
        "get_capacity_used_by_member_before_changes",
    )
    @patch.object(PickupLocationCapacityModeBasketChecker, "get_free_capacity_at_date")
    def test_checkCapacityForBasketSize_newUsageIsEqualToCapacity_returnsTrue(
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
        cache = {}

        result = PickupLocationCapacityModeBasketChecker.check_capacity_for_basket_size(
            basket_size="test_size",
            member=member,
            pickup_location=pickup_location,
            subscription_start=subscription_start,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            cache=cache,
        )

        self.assertTrue(result)

        mock_get_free_capacity_at_date.assert_called_once_with(
            pickup_location=pickup_location,
            basket_size="test_size",
            reference_date=subscription_start,
            cache=cache,
        )
        mock_get_capacity_used_by_member_before_changes.assert_called_once_with(
            member=member,
            subscription_start=subscription_start,
            basket_size="test_size",
            cache=cache,
        )
        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            basket_size="test_size",
            cache=cache,
        )

    @patch.object(
        PickupLocationCapacityModeBasketChecker,
        "calculate_capacity_used_by_the_ordered_products",
    )
    @patch.object(
        PickupLocationCapacityModeBasketChecker,
        "get_capacity_used_by_member_before_changes",
    )
    @patch.object(PickupLocationCapacityModeBasketChecker, "get_free_capacity_at_date")
    def test_checkCapacityForBasketSize_newUsageIsBelowCapacity_returnsTrue(
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
        cache = {}

        result = PickupLocationCapacityModeBasketChecker.check_capacity_for_basket_size(
            basket_size="test_size",
            member=member,
            pickup_location=pickup_location,
            subscription_start=subscription_start,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            cache=cache,
        )

        self.assertTrue(result)

        mock_get_free_capacity_at_date.assert_called_once_with(
            pickup_location=pickup_location,
            basket_size="test_size",
            reference_date=subscription_start,
            cache=cache,
        )
        mock_get_capacity_used_by_member_before_changes.assert_called_once_with(
            member=member,
            subscription_start=subscription_start,
            basket_size="test_size",
            cache=cache,
        )
        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            basket_size="test_size",
            cache=cache,
        )

    @patch.object(
        PickupLocationCapacityModeBasketChecker,
        "calculate_capacity_used_by_the_ordered_products",
    )
    @patch.object(
        PickupLocationCapacityModeBasketChecker,
        "get_capacity_used_by_member_before_changes",
    )
    @patch.object(PickupLocationCapacityModeBasketChecker, "get_free_capacity_at_date")
    def test_checkCapacityForBasketSize_basketSizeIsNotOrdered_returnsTrueAndDontCheckCapacity(
        self,
        mock_get_free_capacity_at_date: Mock,
        mock_get_capacity_used_by_member_before_changes: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
    ):
        mock_get_free_capacity_at_date.return_value = -3
        mock_get_capacity_used_by_member_before_changes.return_value = 0
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 0
        member = Mock()
        pickup_location = Mock()
        subscription_start = Mock()
        ordered_product_to_quantity_map = Mock()
        cache = {}

        result = PickupLocationCapacityModeBasketChecker.check_capacity_for_basket_size(
            basket_size="test_size",
            member=member,
            pickup_location=pickup_location,
            subscription_start=subscription_start,
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            cache=cache,
        )

        self.assertTrue(result)

        mock_get_free_capacity_at_date.assert_not_called()
        mock_get_capacity_used_by_member_before_changes.assert_not_called()
        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            basket_size="test_size",
            cache=cache,
        )
