import datetime
from unittest.mock import patch, MagicMock

from tapir.bestell_wizard.services.products_over_capacity_for_order_provider import (
    ProductsOverCapacityForOrderProvider,
)
from tapir.subscriptions.services.global_capacity_checker import (
    GlobalCapacityChecker,
)
from tapir.wirgarten.tests.factories import ProductFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetProductTypeIds(TapirUnitTest):
    @patch.object(
        GlobalCapacityChecker,
        "get_product_type_ids_without_enough_capacity_for_order",
        autospec=True,
        return_value=["product_type_id"],
    )
    def test_getProductTypeIds_default_delegatesToGlobalCapacityCheckerWithoutMember(
        self, mock_get_product_type_ids_without_enough_capacity_for_order: MagicMock
    ):
        order = {ProductFactory.build(): 2}
        contract_start_date = datetime.date(year=2021, month=3, day=15)
        cache = {}

        result = ProductsOverCapacityForOrderProvider.get_product_type_ids(
            order=order, contract_start_date=contract_start_date, cache=cache
        )

        self.assertEqual(["product_type_id"], result)
        mock_get_product_type_ids_without_enough_capacity_for_order.assert_called_once_with(
            order_with_all_product_types=order,
            member_id=None,
            subscription_start_date=contract_start_date,
            cache=cache,
        )
