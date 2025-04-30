from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.views import CancelSubscriptionsView
from tapir.wirgarten.tests.factories import ProductFactory, ProductTypeFactory


class TestIsAtLeastOneAdditionalProductNotSelected(SimpleTestCase):
    @patch.object(BaseProductTypeService, "get_base_product_type")
    def test_isAtLeastOneAdditionalProductNotSelected_oneAdditionalProductNotSelected_returnsTrue(
        self, mock_get_base_product_type: Mock
    ):
        base_product_type = ProductTypeFactory.build()
        mock_get_base_product_type.return_value = base_product_type
        cache = Mock()

        base_product = ProductFactory.build(type=base_product_type)
        additional_product_selected = ProductFactory.build()
        additional_product_not_selected = ProductFactory.build()
        subscribed_products = {
            base_product,
            additional_product_selected,
            additional_product_not_selected,
        }
        products_selected_for_cancellation = {base_product, additional_product_selected}

        result = (
            CancelSubscriptionsView.is_at_least_one_additional_product_not_selected(
                subscribed_products=subscribed_products,
                products_selected_for_cancellation=products_selected_for_cancellation,
                cache=cache,
            )
        )

        self.assertTrue(result)
        mock_get_base_product_type.assert_called_once_with(cache=cache)

    @patch.object(BaseProductTypeService, "get_base_product_type")
    def test_isAtLeastOneAdditionalProductNotSelected_allAdditionalProductsSelected_returnsFalse(
        self, mock_get_base_product_type: Mock
    ):
        base_product_type = ProductTypeFactory.build()
        mock_get_base_product_type.return_value = base_product_type
        cache = Mock()

        base_product = ProductFactory.build(type=base_product_type)
        additional_product_1 = ProductFactory.build()
        additional_product_2 = ProductFactory.build()
        subscribed_products = {
            base_product,
            additional_product_1,
            additional_product_2,
        }
        products_selected_for_cancellation = {
            additional_product_1,
            additional_product_2,
        }

        result = (
            CancelSubscriptionsView.is_at_least_one_additional_product_not_selected(
                subscribed_products=subscribed_products,
                products_selected_for_cancellation=products_selected_for_cancellation,
                cache=cache,
            )
        )

        self.assertFalse(result)
        mock_get_base_product_type.assert_called_once_with(cache=cache)
