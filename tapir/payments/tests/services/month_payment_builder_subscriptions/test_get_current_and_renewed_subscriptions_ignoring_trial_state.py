import datetime
from unittest.mock import Mock, patch

from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetCurrentAndRenewedSubscriptionsIgnoringTrialState(TapirUnitTest):
    @patch.object(TrialPeriodManager, "is_contract_in_trial", autospec=True)
    @patch.object(
        AutomaticSubscriptionRenewalService,
        "build_renewed_subscription",
        autospec=True,
    )
    @patch.object(
        AutomaticSubscriptionRenewalService,
        "get_subscriptions_that_will_be_renewed",
        autospec=True,
    )
    @patch.object(TapirCache, "get_all_subscriptions", autospec=True)
    def test_getCurrentAndRenewedSubscriptionsIgnoringTrialState_default_returnsExistingAndRenewedWithoutTrialFilter(
        self,
        mock_get_all_subscriptions: Mock,
        mock_get_subscriptions_that_will_be_renewed: Mock,
        mock_build_renewed_subscription: Mock,
        mock_is_contract_in_trial: Mock,
    ):
        existing_subscription = SubscriptionFactory.build()
        subscription_to_renew = SubscriptionFactory.build()
        renewed_subscription = SubscriptionFactory.build()
        mock_get_all_subscriptions.return_value = {existing_subscription}
        mock_get_subscriptions_that_will_be_renewed.return_value = {
            subscription_to_renew
        }
        mock_build_renewed_subscription.return_value = renewed_subscription
        first_of_month = datetime.date(year=2025, month=9, day=1)
        cache = Mock()

        result = MonthPaymentBuilderSubscriptions.get_current_and_renewed_subscriptions_ignoring_trial_state(
            first_of_month=first_of_month, cache=cache
        )

        self.assertEqual({existing_subscription, renewed_subscription}, result)
        mock_get_all_subscriptions.assert_called_once_with(cache=cache)
        mock_get_subscriptions_that_will_be_renewed.assert_called_once_with(
            reference_date=first_of_month, cache=cache
        )
        mock_build_renewed_subscription.assert_called_once_with(
            subscription=subscription_to_renew, cache=cache
        )
        mock_is_contract_in_trial.assert_not_called()
