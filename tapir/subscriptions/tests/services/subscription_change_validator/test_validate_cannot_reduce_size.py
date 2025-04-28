from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)


class TestValidateCannotReduceSize(SimpleTestCase):
    @patch.object(
        SubscriptionChangeValidator, "calculate_capacity_used_by_the_ordered_products"
    )
    @patch.object(SubscriptionChangeValidator, "should_validate_cannot_reduce_size")
    def test_validateCannotReduceSize_shouldNotValidate_doesNothing(
        self,
        mock_should_validate_cannot_reduce_size: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
    ):
        mock_should_validate_cannot_reduce_size.return_value = False

        SubscriptionChangeValidator.validate_cannot_reduce_size(
            logged_in_user_is_admin=False,
            subscription_start_date=Mock(),
            member_id="invalid",
            form=Mock(),
            field_prefix="invalid",
            product_type_id="invalid",
            cache=Mock(),
        )

        mock_calculate_capacity_used_by_the_ordered_products.assert_not_called()

    @patch.object(
        SubscriptionChangeValidator,
        "calculate_capacity_used_by_the_current_subscriptions",
    )
    @patch.object(
        SubscriptionChangeValidator, "calculate_capacity_used_by_the_ordered_products"
    )
    @patch.object(SubscriptionChangeValidator, "should_validate_cannot_reduce_size")
    def test_validateCannotReduceSize_orderedProductsAreLessThanCurrent_raisesError(
        self,
        mock_should_validate_cannot_reduce_size: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
        mock_calculate_capacity_used_by_the_current_subscriptions: Mock,
    ):
        mock_should_validate_cannot_reduce_size.return_value = True

        mock_calculate_capacity_used_by_the_ordered_products.return_value = 1
        mock_calculate_capacity_used_by_the_current_subscriptions.return_value = 2

        form = Mock()
        field_prefix = "test_field_prefix"
        cache = Mock()
        product_type_id = "test_product_type_id"
        member_id = "test_member_id"

        with self.assertRaises(ValidationError):
            SubscriptionChangeValidator.validate_cannot_reduce_size(
                logged_in_user_is_admin=False,
                subscription_start_date=Mock(),
                member_id=member_id,
                form=form,
                field_prefix=field_prefix,
                product_type_id=product_type_id,
                cache=cache,
            )

        mock_calculate_capacity_used_by_the_ordered_products.assert_called_once_with(
            form=form,
            return_capacity_in_euros=False,
            field_prefix=field_prefix,
            cache=cache,
        )
        mock_calculate_capacity_used_by_the_current_subscriptions.assert_called_once_with(
            product_type_id=product_type_id, member_id=member_id, cache=cache
        )

    @patch.object(
        SubscriptionChangeValidator,
        "calculate_capacity_used_by_the_current_subscriptions",
    )
    @patch.object(
        SubscriptionChangeValidator, "calculate_capacity_used_by_the_ordered_products"
    )
    @patch.object(SubscriptionChangeValidator, "should_validate_cannot_reduce_size")
    def test_validateCannotReduceSize_orderedProductsAreSameAsCurrent_doesNothing(
        self,
        mock_should_validate_cannot_reduce_size: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
        mock_calculate_capacity_used_by_the_current_subscriptions: Mock,
    ):
        mock_should_validate_cannot_reduce_size.return_value = True

        mock_calculate_capacity_used_by_the_ordered_products.return_value = 2
        mock_calculate_capacity_used_by_the_current_subscriptions.return_value = 2

        form = Mock()
        field_prefix = "test_field_prefix"
        cache = Mock()
        product_type_id = "test_product_type_id"
        member_id = "test_member_id"

        SubscriptionChangeValidator.validate_cannot_reduce_size(
            logged_in_user_is_admin=False,
            subscription_start_date=Mock(),
            member_id=member_id,
            form=form,
            field_prefix=field_prefix,
            product_type_id=product_type_id,
            cache=cache,
        )

    @patch.object(
        SubscriptionChangeValidator,
        "calculate_capacity_used_by_the_current_subscriptions",
    )
    @patch.object(
        SubscriptionChangeValidator, "calculate_capacity_used_by_the_ordered_products"
    )
    @patch.object(SubscriptionChangeValidator, "should_validate_cannot_reduce_size")
    def test_validateCannotReduceSize_orderedProductsAreBiggerThanCurrent_doesNothing(
        self,
        mock_should_validate_cannot_reduce_size: Mock,
        mock_calculate_capacity_used_by_the_ordered_products: Mock,
        mock_calculate_capacity_used_by_the_current_subscriptions: Mock,
    ):
        mock_should_validate_cannot_reduce_size.return_value = True

        mock_calculate_capacity_used_by_the_ordered_products.return_value = 3
        mock_calculate_capacity_used_by_the_current_subscriptions.return_value = 2

        form = Mock()
        field_prefix = "test_field_prefix"
        cache = Mock()
        product_type_id = "test_product_type_id"
        member_id = "test_member_id"

        SubscriptionChangeValidator.validate_cannot_reduce_size(
            logged_in_user_is_admin=False,
            subscription_start_date=Mock(),
            member_id=member_id,
            form=form,
            field_prefix=field_prefix,
            product_type_id=product_type_id,
            cache=cache,
        )
