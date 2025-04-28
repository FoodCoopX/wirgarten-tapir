from unittest.mock import Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)
from tapir.wirgarten.tests.factories import ProductTypeFactory


class TestValidateSingleSubscription(SimpleTestCase):
    def test_validateSingleSubscription_productTypeAllowsSeveralSubscriptions_doesNothing(
        self,
    ):
        SubscriptionChangeValidator.validate_single_subscription(
            form=Mock(),
            field_prefix="invalid",
            product_type=ProductTypeFactory.build(single_subscription_only=False),
        )

    def test_validateSingleSubscription_productIsOrderedOnce_doesNothing(
        self,
    ):
        form = Mock()
        form.cleaned_data = {"testprefix_productA": False, "testprefix_productB": True}
        SubscriptionChangeValidator.validate_single_subscription(
            form=form,
            field_prefix="testprefix",
            product_type=ProductTypeFactory.build(single_subscription_only=True),
        )

    def test_validateSingleSubscription_productIsNotOrdered_doesNothing(
        self,
    ):
        form = Mock()
        form.cleaned_data = {"testprefix_productA": False, "testprefix_productB": False}
        SubscriptionChangeValidator.validate_single_subscription(
            form=form,
            field_prefix="testprefix",
            product_type=ProductTypeFactory.build(single_subscription_only=True),
        )

    def test_validateSingleSubscription_productIsOrderedSeveralTimes_raisesError(
        self,
    ):
        form = Mock()
        form.cleaned_data = {"testprefix_productA": True, "testprefix_productB": True}
        with self.assertRaises(ValidationError):
            SubscriptionChangeValidator.validate_single_subscription(
                form=form,
                field_prefix="testprefix",
                product_type=ProductTypeFactory.build(single_subscription_only=True),
            )
