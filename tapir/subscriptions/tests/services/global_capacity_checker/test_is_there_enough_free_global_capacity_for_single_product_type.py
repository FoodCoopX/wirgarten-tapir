from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.subscriptions.services.product_type_lowest_free_capacity_after_date_generic import (
    ProductTypeLowestFreeCapacityAfterDateCalculator,
)
from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)
from tapir.waiting_list.services.waiting_list_reserved_capacity_calculator import (
    WaitingListReservedCapacityCalculator,
)


class TestIsThereEnoughFreeGlobalCapacityForSingleProductType(SimpleTestCase):
    @patch.object(
        WaitingListReservedCapacityCalculator,
        "calculate_capacity_reserved_by_the_waiting_list_entries",
        autospec=True,
    )
    @patch.object(
        SubscriptionChangeValidator,
        "calculate_capacity_used_by_the_current_subscriptions",
        autospec=True,
    )
    @patch.object(
        GlobalCapacityChecker,
        "calculate_global_capacity_used_by_the_ordered_products",
        autospec=True,
    )
    @patch.object(
        ProductTypeLowestFreeCapacityAfterDateCalculator,
        "get_lowest_free_capacity_after_date",
        autospec=True,
    )
    def test_isThereEnoughFreeGlobalCapacityForSingleProductType_enoughFreeCapacity_returnsTrue(
        self,
        mock_get_lowest_free_capacity_after_date: Mock,
        mock_calculate_global_capacity_used_by_the_ordered_products: Mock,
        mock_calculate_capacity_used_by_the_current_subscriptions: Mock,
        mock_calculate_capacity_reserved_by_the_waiting_list_entries: Mock,
    ):
        mock_get_lowest_free_capacity_after_date.return_value = 3
        mock_calculate_global_capacity_used_by_the_ordered_products.return_value = 4
        mock_calculate_capacity_used_by_the_current_subscriptions.return_value = 2

        order = Mock()
        member_id = "test_member_id"
        subscription_start_date = Mock()
        product_type_id = "test_product_type_id"
        product_type = Mock()
        cache = {"product_types_by_id": {"test_product_type_id": product_type}}

        result = GlobalCapacityChecker.is_there_enough_free_global_capacity_for_single_product_type(
            order_for_a_single_product_type=order,
            member_id=member_id,
            subscription_start_date=subscription_start_date,
            product_type_id=product_type_id,
            check_waiting_list_entries=False,
            cache=cache,
        )

        mock_get_lowest_free_capacity_after_date.assert_called_once_with(
            product_type=product_type,
            reference_date=subscription_start_date,
            cache=cache,
        )
        mock_calculate_global_capacity_used_by_the_ordered_products.assert_called_once_with(
            order_for_a_single_product_type=order,
            reference_date=subscription_start_date,
            cache=cache,
        )
        mock_calculate_capacity_used_by_the_current_subscriptions.assert_called_once_with(
            product_type_id=product_type_id,
            member_id=member_id,
            subscription_start_date=subscription_start_date,
            cache=cache,
        )
        mock_calculate_capacity_reserved_by_the_waiting_list_entries.assert_not_called()

        self.assertTrue(result)

    @patch.object(
        WaitingListReservedCapacityCalculator,
        "calculate_capacity_reserved_by_the_waiting_list_entries",
        autospec=True,
    )
    @patch.object(
        SubscriptionChangeValidator,
        "calculate_capacity_used_by_the_current_subscriptions",
        autospec=True,
    )
    @patch.object(
        GlobalCapacityChecker,
        "calculate_global_capacity_used_by_the_ordered_products",
        autospec=True,
    )
    @patch.object(
        ProductTypeLowestFreeCapacityAfterDateCalculator,
        "get_lowest_free_capacity_after_date",
        autospec=True,
    )
    def test_isThereEnoughFreeGlobalCapacityForSingleProductType_exactlyEnoughFreeCapacity_returnsTrue(
        self,
        mock_get_lowest_free_capacity_after_date: Mock,
        mock_calculate_global_capacity_used_by_the_ordered_products: Mock,
        mock_calculate_capacity_used_by_the_current_subscriptions: Mock,
        mock_calculate_capacity_reserved_by_the_waiting_list_entries: Mock,
    ):
        mock_get_lowest_free_capacity_after_date.return_value = 3
        mock_calculate_global_capacity_used_by_the_ordered_products.return_value = 4
        mock_calculate_capacity_used_by_the_current_subscriptions.return_value = 1

        order = Mock()
        member_id = "test_member_id"
        subscription_start_date = Mock()
        product_type_id = "test_product_type_id"
        product_type = Mock()
        cache = {"product_types_by_id": {"test_product_type_id": product_type}}

        result = GlobalCapacityChecker.is_there_enough_free_global_capacity_for_single_product_type(
            order_for_a_single_product_type=order,
            member_id=member_id,
            subscription_start_date=subscription_start_date,
            product_type_id=product_type_id,
            check_waiting_list_entries=False,
            cache=cache,
        )

        mock_get_lowest_free_capacity_after_date.assert_called_once_with(
            product_type=product_type,
            reference_date=subscription_start_date,
            cache=cache,
        )
        mock_calculate_global_capacity_used_by_the_ordered_products.assert_called_once_with(
            order_for_a_single_product_type=order,
            reference_date=subscription_start_date,
            cache=cache,
        )
        mock_calculate_capacity_used_by_the_current_subscriptions.assert_called_once_with(
            product_type_id=product_type_id,
            member_id=member_id,
            subscription_start_date=subscription_start_date,
            cache=cache,
        )
        mock_calculate_capacity_reserved_by_the_waiting_list_entries.assert_not_called()

        self.assertTrue(result)

    @patch.object(
        WaitingListReservedCapacityCalculator,
        "calculate_capacity_reserved_by_the_waiting_list_entries",
        autospec=True,
    )
    @patch.object(
        SubscriptionChangeValidator,
        "calculate_capacity_used_by_the_current_subscriptions",
        autospec=True,
    )
    @patch.object(
        GlobalCapacityChecker,
        "calculate_global_capacity_used_by_the_ordered_products",
        autospec=True,
    )
    @patch.object(
        ProductTypeLowestFreeCapacityAfterDateCalculator,
        "get_lowest_free_capacity_after_date",
        autospec=True,
    )
    def test_isThereEnoughFreeGlobalCapacityForSingleProductType_notEnoughCapacity_returnsFalse(
        self,
        mock_get_lowest_free_capacity_after_date: Mock,
        mock_calculate_global_capacity_used_by_the_ordered_products: Mock,
        mock_calculate_capacity_used_by_the_current_subscriptions: Mock,
        mock_calculate_capacity_reserved_by_the_waiting_list_entries: Mock,
    ):
        mock_get_lowest_free_capacity_after_date.return_value = 3
        mock_calculate_global_capacity_used_by_the_ordered_products.return_value = 4
        mock_calculate_capacity_used_by_the_current_subscriptions.return_value = 0

        order = Mock()
        member_id = "test_member_id"
        subscription_start_date = Mock()
        product_type_id = "test_product_type_id"
        product_type = Mock()
        cache = {"product_types_by_id": {"test_product_type_id": product_type}}

        result = GlobalCapacityChecker.is_there_enough_free_global_capacity_for_single_product_type(
            order_for_a_single_product_type=order,
            member_id=member_id,
            subscription_start_date=subscription_start_date,
            product_type_id=product_type_id,
            check_waiting_list_entries=False,
            cache=cache,
        )

        mock_get_lowest_free_capacity_after_date.assert_called_once_with(
            product_type=product_type,
            reference_date=subscription_start_date,
            cache=cache,
        )
        mock_calculate_global_capacity_used_by_the_ordered_products.assert_called_once_with(
            order_for_a_single_product_type=order,
            reference_date=subscription_start_date,
            cache=cache,
        )
        mock_calculate_capacity_used_by_the_current_subscriptions.assert_called_once_with(
            product_type_id=product_type_id,
            member_id=member_id,
            subscription_start_date=subscription_start_date,
            cache=cache,
        )
        mock_calculate_capacity_reserved_by_the_waiting_list_entries.assert_not_called()

        self.assertFalse(result)

    @patch.object(
        WaitingListReservedCapacityCalculator,
        "calculate_capacity_reserved_by_the_waiting_list_entries",
        autospec=True,
    )
    @patch.object(
        SubscriptionChangeValidator,
        "calculate_capacity_used_by_the_current_subscriptions",
        autospec=True,
    )
    @patch.object(
        GlobalCapacityChecker,
        "calculate_global_capacity_used_by_the_ordered_products",
        autospec=True,
    )
    @patch.object(
        ProductTypeLowestFreeCapacityAfterDateCalculator,
        "get_lowest_free_capacity_after_date",
        autospec=True,
    )
    def test_isThereEnoughFreeGlobalCapacityForSingleProductType_checkWaitingList_useWaitingList(
        self,
        mock_get_lowest_free_capacity_after_date: Mock,
        mock_calculate_global_capacity_used_by_the_ordered_products: Mock,
        mock_calculate_capacity_used_by_the_current_subscriptions: Mock,
        mock_calculate_capacity_reserved_by_the_waiting_list_entries: Mock,
    ):
        mock_get_lowest_free_capacity_after_date.return_value = 4
        mock_calculate_global_capacity_used_by_the_ordered_products.return_value = 3
        mock_calculate_capacity_used_by_the_current_subscriptions.return_value = 0
        mock_calculate_capacity_reserved_by_the_waiting_list_entries.return_value = 2

        order = Mock()
        member_id = "test_member_id"
        subscription_start_date = Mock()
        product_type_id = "test_product_type_id"
        product_type = Mock()
        cache = {"product_types_by_id": {"test_product_type_id": product_type}}

        result = GlobalCapacityChecker.is_there_enough_free_global_capacity_for_single_product_type(
            order_for_a_single_product_type=order,
            member_id=member_id,
            subscription_start_date=subscription_start_date,
            product_type_id=product_type_id,
            check_waiting_list_entries=True,
            cache=cache,
        )

        mock_calculate_capacity_reserved_by_the_waiting_list_entries.assert_called_once_with(
            product_type_id=product_type_id,
            pickup_location=None,
            reference_date=subscription_start_date,
            cache=cache,
        )

        self.assertFalse(result)
