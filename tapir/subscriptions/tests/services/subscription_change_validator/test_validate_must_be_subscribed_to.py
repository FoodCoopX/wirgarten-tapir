from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)
from tapir.wirgarten.tests.factories import ProductTypeFactory


class TestValidateMustBeSubscribedTo(SimpleTestCase):
    def test_validateMustBeSubscribedTo_productIsNotRequired_doesNothing(self):
        product_type = ProductTypeFactory.build(must_be_subscribed_to=False)

        SubscriptionChangeValidator.validate_must_be_subscribed_to(
            form=Mock(), field_prefix="invalid", product_type=product_type, cache=Mock()
        )

    @patch.object(
        SubscriptionChangeValidator, "calculate_capacity_used_by_the_ordered_products"
    )
    def test_validateMustBeSubscribedTo_productIsRequiredAndOrdered_doesNothing(
        self, mock_calculate_capacity_used_by_the_ordered_products: Mock
    ):
        product_type = ProductTypeFactory.build(must_be_subscribed_to=True)
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 1

        form = Mock()
        field_prefix = "test_field_prefix"
        cache = Mock()

        SubscriptionChangeValidator.validate_must_be_subscribed_to(
            form=form, field_prefix=field_prefix, product_type=product_type, cache=cache
        )

        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            form=form,
            return_capacity_in_euros=False,
            field_prefix=field_prefix,
            cache=cache,
        )

    @patch.object(
        SubscriptionChangeValidator, "calculate_capacity_used_by_the_ordered_products"
    )
    def test_validateMustBeSubscribedTo_productIsRequiredButNotOrdered_raisesError(
        self, mock_calculate_capacity_used_by_the_ordered_products: Mock
    ):
        product_type = ProductTypeFactory.build(must_be_subscribed_to=True)
        mock_calculate_capacity_used_by_the_ordered_products.return_value = 0

        form = Mock()
        field_prefix = "test_field_prefix"
        cache = Mock()

        with self.assertRaises(ValidationError):
            SubscriptionChangeValidator.validate_must_be_subscribed_to(
                form=form,
                field_prefix=field_prefix,
                product_type=product_type,
                cache=cache,
            )

        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            form=form,
            return_capacity_in_euros=False,
            field_prefix=field_prefix,
            cache=cache,
        )
