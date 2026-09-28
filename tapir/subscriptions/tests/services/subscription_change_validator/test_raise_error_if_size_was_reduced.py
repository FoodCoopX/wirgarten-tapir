from django.core.exceptions import ValidationError
from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)


class TestRaiseErrorIfSizeWasReduced(TapirUnitTest):
    def test_raiseErrorIfSizeWasReduced_orderedIsLessThanCurrent_raisesError(self):
        with self.assertRaises(ValidationError):
            SubscriptionChangeValidator.raise_error_if_size_was_reduced(
                capacity_used_by_the_ordered_products=1,
                capacity_used_by_the_current_subscriptions=2,
            )

    def test_raiseErrorIfSizeWasReduced_orderedIsSameAsCurrent_doesNothing(self):
        SubscriptionChangeValidator.raise_error_if_size_was_reduced(
            capacity_used_by_the_ordered_products=2,
            capacity_used_by_the_current_subscriptions=2,
        )

    def test_raiseErrorIfSizeWasReduced_orderedIsBiggerThanCurrent_doesNothing(self):
        SubscriptionChangeValidator.raise_error_if_size_was_reduced(
            capacity_used_by_the_ordered_products=3,
            capacity_used_by_the_current_subscriptions=2,
        )
