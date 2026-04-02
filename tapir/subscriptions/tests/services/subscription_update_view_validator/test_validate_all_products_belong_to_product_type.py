from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.subscriptions.services.subscription_update_view_validator import (
    SubscriptionUpdateViewValidator,
)
from tapir.utils.services.tapir_cache import TapirCache


@patch.object(TapirCache, "get_product_by_id", autospec=True)
class TestSubscriptionUpdateViewValidatorValidateAllProductsBelongToProductType(
    SimpleTestCase,
):
    def test_validateAllProductsBelongToProductType_emptyOrder_noErrorRaised(
        self,
        mock_get_product_by_id: Mock,
    ):
        SubscriptionUpdateViewValidator.validate_all_products_belong_to_product_type(
            order={}, product_type_id="test_product_type_id", cache={}
        )

        mock_get_product_by_id.assert_not_called()

    def test_validateAllProductsBelongToProductType_allProductsBelongToProductType_noErrorRaised(
        self,
        mock_get_product_by_id: Mock,
    ):
        product_type_id = "test_product_type_id"
        product_a = Mock()
        product_b = Mock()
        cached_product_a = Mock(type_id=product_type_id)
        cached_product_b = Mock(type_id=product_type_id)
        mock_get_product_by_id.side_effect = [cached_product_a, cached_product_b]
        cache = Mock()

        SubscriptionUpdateViewValidator.validate_all_products_belong_to_product_type(
            order={product_a: 1, product_b: 2},
            product_type_id=product_type_id,
            cache=cache,
        )

        self.assertEqual(2, mock_get_product_by_id.call_count)

    def test_validateAllProductsBelongToProductType_oneProductHasADifferentProductType_raisesValidationError(
        self,
        mock_get_product_by_id: Mock,
    ):
        product_type_id = "test_product_type_id"
        product_a = Mock()
        product_b = Mock()
        cached_product_a = Mock(type_id=product_type_id)
        cached_product_b = Mock(type_id="other_product_type_id")
        cached_product_b.name = "Product B"
        mock_get_product_by_id.side_effect = [cached_product_a, cached_product_b]
        cache = Mock()

        with self.assertRaises(ValidationError) as error:
            SubscriptionUpdateViewValidator.validate_all_products_belong_to_product_type(
                order={product_a: 1, product_b: 2},
                product_type_id=product_type_id,
                cache=cache,
            )

        self.assertEqual(
            f"Product 'Product B' does not belong to product type with id: {product_type_id}",
            error.exception.message,
        )
