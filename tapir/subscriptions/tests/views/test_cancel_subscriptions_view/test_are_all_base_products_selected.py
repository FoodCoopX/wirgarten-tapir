from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.views.cancellations import CancelSubscriptionsView
from tapir.wirgarten.tests.factories import ProductTypeFactory, ProductFactory


class TestAreAllBaseProductsSelected(SimpleTestCase):
    @patch.object(BaseProductTypeService, "get_base_product_type")
    def test_areAllBaseProductsSelected_allBaseProductsSelected_returnsTrue(
        self, mock_get_base_product_type: Mock
    ):
        base_product_type = ProductTypeFactory.build()
        mock_get_base_product_type.return_value = base_product_type
        cache = Mock()

        base_product_1 = ProductFactory.build(type=base_product_type)
        base_product_2 = ProductFactory.build(type=base_product_type)
        additional_product = ProductFactory.build()
        subscribed_products = {
            base_product_1,
            base_product_2,
            additional_product,
        }
        products_selected_for_cancellation = {base_product_1, base_product_2}

        result = CancelSubscriptionsView.are_all_base_products_selected(
            subscribed_products=subscribed_products,
            products_selected_for_cancellation=products_selected_for_cancellation,
            cache=cache,
        )

        self.assertTrue(result)
        mock_get_base_product_type.assert_called_once_with(cache=cache)

    @patch.object(BaseProductTypeService, "get_base_product_type")
    def test_areAllBaseProductsSelected_notAllBaseProductsSelected_returnsFalse(
        self, mock_get_base_product_type: Mock
    ):
        base_product_type = ProductTypeFactory.build()
        mock_get_base_product_type.return_value = base_product_type
        cache = Mock()

        base_product_1 = ProductFactory.build(type=base_product_type)
        base_product_2 = ProductFactory.build(type=base_product_type)
        additional_product = ProductFactory.build()
        subscribed_products = {
            base_product_1,
            base_product_2,
            additional_product,
        }
        products_selected_for_cancellation = {base_product_2}

        result = CancelSubscriptionsView.are_all_base_products_selected(
            subscribed_products=subscribed_products,
            products_selected_for_cancellation=products_selected_for_cancellation,
            cache=cache,
        )

        self.assertFalse(result)
        mock_get_base_product_type.assert_called_once_with(cache=cache)
