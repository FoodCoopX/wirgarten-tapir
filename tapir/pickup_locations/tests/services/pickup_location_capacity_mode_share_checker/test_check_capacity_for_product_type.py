from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.waiting_list.services.waiting_list_reserved_capacity_calculator import (
    WaitingListReservedCapacityCalculator,
)


class TestCheckCapacityForProductType(SimpleTestCase):
    @patch.object(
        WaitingListReservedCapacityCalculator,
        "calculate_capacity_reserved_by_the_waiting_list_entries",
        autospec=True,
    )
    @patch.object(
        PickupLocationCapacityModeShareChecker,
        "calculate_capacity_used_by_the_ordered_products",
        autospec=True,
    )
    @patch.object(
        PickupLocationCapacityModeShareChecker,
        "get_capacity_used_by_member_before_changes",
        autospec=True,
    )
    @patch.object(
        PickupLocationCapacityModeShareChecker,
        "get_free_capacity_at_date",
        autospec=True,
    )
    def test_checkCapacityForProductType_newUsageIsOverCapacity_returnsFalse(
        self,
        mock_get_free_capacity_at_date: Mock,
        mock_get_capacity_used_by_member_before_changes: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
        mock_calculate_capacity_reserved_by_the_waiting_list_entries: Mock,
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
            check_waiting_list_entries=False,
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
        mock_calculate_capacity_reserved_by_the_waiting_list_entries.assert_not_called()

    @patch.object(
        WaitingListReservedCapacityCalculator,
        "calculate_capacity_reserved_by_the_waiting_list_entries",
        autospec=True,
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
        mock_calculate_capacity_reserved_by_the_waiting_list_entries: Mock,
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
            check_waiting_list_entries=False,
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
        mock_calculate_capacity_reserved_by_the_waiting_list_entries.assert_not_called()

    @patch.object(
        WaitingListReservedCapacityCalculator,
        "calculate_capacity_reserved_by_the_waiting_list_entries",
        autospec=True,
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
        mock_calculate_capacity_reserved_by_the_waiting_list_entries: Mock,
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
            check_waiting_list_entries=False,
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
        mock_calculate_capacity_reserved_by_the_waiting_list_entries.assert_not_called(),

    @patch.object(
        WaitingListReservedCapacityCalculator,
        "calculate_capacity_reserved_by_the_waiting_list_entries",
        autospec=True,
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
    def test_checkCapacityForProductType_productTypeIsNotPartOfOrder_returnsTrueAndDontCheckCapacity(
        self,
        mock_get_free_capacity_at_date: Mock,
        mock_get_capacity_used_by_member_before_changes: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
        mock_calculate_capacity_reserved_by_the_waiting_list_entries: Mock,
    ):
        mock_get_free_capacity_at_date.return_value = -4
        mock_get_capacity_used_by_member_before_changes.return_value = 0
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 0
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
            check_waiting_list_entries=False,
            cache=cache,
        )

        self.assertTrue(result)

        mock_get_free_capacity_at_date.assert_not_called()
        mock_get_capacity_used_by_member_before_changes.assert_not_called()
        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            product_type=product_type,
            reference_date=subscription_start,
            cache=cache,
        )
        mock_calculate_capacity_reserved_by_the_waiting_list_entries.assert_not_called()

    @patch.object(
        WaitingListReservedCapacityCalculator,
        "calculate_capacity_reserved_by_the_waiting_list_entries",
        autospec=True,
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
    def test_checkCapacityForProductType_checkWaitingListEntry_useWaitingListCheck(
        self,
        mock_get_free_capacity_at_date: Mock,
        mock_get_capacity_used_by_member_before_changes: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
        mock_calculate_capacity_reserved_by_the_waiting_list_entries: Mock,
    ):
        mock_get_free_capacity_at_date.return_value = 2
        mock_get_capacity_used_by_member_before_changes.return_value = 0
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 1
        mock_calculate_capacity_reserved_by_the_waiting_list_entries.return_value = 2
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
            check_waiting_list_entries=True,
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
        mock_calculate_capacity_reserved_by_the_waiting_list_entries.assert_called_once_with(
            product_type_id=product_type.id,
            pickup_location=pickup_location,
            reference_date=subscription_start,
            cache=cache,
        ),
