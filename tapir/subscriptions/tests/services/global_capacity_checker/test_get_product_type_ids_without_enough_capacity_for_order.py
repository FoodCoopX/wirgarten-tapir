from unittest.mock import Mock, patch, call

from django.test import SimpleTestCase

from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.wirgarten.tests.factories import ProductFactory


class TestGetProductTypeIdsWithoutEnoughCapacityForOrder(SimpleTestCase):
    @patch.object(
        GlobalCapacityChecker,
        "is_there_enough_free_global_capacity_for_single_product_type",
        autospec=True,
    )
    def test_getProductTypeIdsWithoutEnoughCapacityForOrder_default_returnsCorrectTypeIds(
        self, mock_is_there_enough_free_global_capacity_for_single_product_type: Mock
    ):
        member_id = "test_member_id"
        cache = {}
        subscription_start_date = Mock()
        product_1 = ProductFactory.build()
        product_2 = ProductFactory.build()
        product_3 = ProductFactory.build()
        product_4 = ProductFactory.build(type=product_1.type)
        order_with_all_product_types = {
            product_1: 1,
            product_2: 2,
            product_3: 3,
            product_4: 4,
        }

        mock_is_there_enough_free_global_capacity_for_single_product_type.side_effect = (
            lambda order_for_a_single_product_type, member_id, subscription_start_date, product_type_id, check_waiting_list_entries, cache: product_type_id
            == product_2.type_id
        )

        result = GlobalCapacityChecker.get_product_type_ids_without_enough_capacity_for_order(
            order_with_all_product_types=order_with_all_product_types,
            member_id=member_id,
            subscription_start_date=subscription_start_date,
            cache=cache,
        )

        self.assertEqual({product_1.type_id, product_3.type_id}, set(result))
        self.assertEqual(
            3,
            mock_is_there_enough_free_global_capacity_for_single_product_type.call_count,
        )
        mock_is_there_enough_free_global_capacity_for_single_product_type.assert_has_calls(
            [
                call(
                    order_for_a_single_product_type={product_1: 1, product_4: 4},
                    member_id=member_id,
                    subscription_start_date=subscription_start_date,
                    product_type_id=product_1.type_id,
                    check_waiting_list_entries=True,
                    cache=cache,
                ),
                call(
                    order_for_a_single_product_type={product_2: 2},
                    member_id=member_id,
                    subscription_start_date=subscription_start_date,
                    product_type_id=product_2.type_id,
                    check_waiting_list_entries=True,
                    cache=cache,
                ),
                call(
                    order_for_a_single_product_type={product_3: 3},
                    member_id=member_id,
                    subscription_start_date=subscription_start_date,
                    product_type_id=product_3.type_id,
                    check_waiting_list_entries=True,
                    cache=cache,
                ),
            ],
            any_order=True,
        )
