import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import SubscriptionFactory


class TestGetCurrentAndRenewedSubscriptions(SimpleTestCase):
    @patch.object(TrialPeriodManager, "is_contract_in_trial", autospec=True)
    @patch.object(
        AutomaticSubscriptionRenewalService,
        "get_subscriptions_that_will_be_renewed",
        autospec=True,
    )
    @patch.object(TapirCache, "get_all_subscriptions", autospec=True)
    def test_getCurrentAndRenewedSubscription_existingSubscriptionDoesNotFitTrialParam_subscriptionNotReturned(
        self,
        mock_get_all_subscriptions: Mock,
        mock_get_subscriptions_that_will_be_renewed: Mock,
        mock_is_contract_in_trial: Mock,
    ):
        subscription = SubscriptionFactory.build()
        mock_get_all_subscriptions.return_value = {subscription}
        mock_get_subscriptions_that_will_be_renewed.return_value = set()
        mock_is_contract_in_trial.return_value = False
        first_of_month = datetime.date(year=2025, month=9, day=18)
        cache = Mock()

        result = MonthPaymentBuilderSubscriptions.get_current_and_renewed_subscriptions(
            first_of_month=first_of_month, is_in_trial=True, cache=cache
        )

        self.assertEqual([], result)

        mock_get_all_subscriptions.assert_called_once_with(cache=cache)
        mock_get_subscriptions_that_will_be_renewed.assert_called_once_with(
            reference_date=first_of_month, cache=cache
        )
        mock_is_contract_in_trial.assert_called_once_with(
            contract=subscription, cache=cache, reference_date=first_of_month
        )

    @patch.object(TrialPeriodManager, "is_contract_in_trial", autospec=True)
    @patch.object(
        AutomaticSubscriptionRenewalService,
        "get_subscriptions_that_will_be_renewed",
        autospec=True,
    )
    @patch.object(TapirCache, "get_all_subscriptions", autospec=True)
    def test_getCurrentAndRenewedSubscription_existingSubscriptionDoesFitsTrialParam_subscriptionReturned(
        self,
        mock_get_all_subscriptions: Mock,
        mock_get_subscriptions_that_will_be_renewed: Mock,
        mock_is_contract_in_trial: Mock,
    ):
        subscription = SubscriptionFactory.build()
        mock_get_all_subscriptions.return_value = {subscription}
        mock_get_subscriptions_that_will_be_renewed.return_value = set()
        mock_is_contract_in_trial.return_value = True
        first_of_month = datetime.date(year=2025, month=9, day=18)
        cache = Mock()

        result = MonthPaymentBuilderSubscriptions.get_current_and_renewed_subscriptions(
            first_of_month=first_of_month, is_in_trial=True, cache=cache
        )

        self.assertEqual([subscription], result)

        mock_get_all_subscriptions.assert_called_once_with(cache=cache)
        mock_get_subscriptions_that_will_be_renewed.assert_called_once_with(
            reference_date=first_of_month, cache=cache
        )
        mock_is_contract_in_trial.assert_called_once_with(
            contract=subscription, cache=cache, reference_date=first_of_month
        )

    @patch.object(TrialPeriodManager, "is_contract_in_trial", autospec=True)
    @patch.object(
        AutomaticSubscriptionRenewalService, "build_renewed_subscription", autospec=True
    )
    @patch.object(
        AutomaticSubscriptionRenewalService,
        "get_subscriptions_that_will_be_renewed",
        autospec=True,
    )
    @patch.object(TapirCache, "get_all_subscriptions", autospec=True)
    def test_getCurrentAndRenewedSubscription_renewedSubscriptionDoesNotFitTrialParam_subscriptionNotReturned(
        self,
        mock_get_all_subscriptions: Mock,
        mock_get_subscriptions_that_will_be_renewed: Mock,
        mock_build_renewed_subscription: Mock,
        mock_is_contract_in_trial: Mock,
    ):
        original_subscription = SubscriptionFactory.build()
        renewed_subscription = SubscriptionFactory.build()
        mock_get_all_subscriptions.return_value = set()
        mock_get_subscriptions_that_will_be_renewed.return_value = {
            original_subscription
        }
        mock_build_renewed_subscription.return_value = renewed_subscription
        mock_is_contract_in_trial.return_value = True
        first_of_month = datetime.date(year=2025, month=9, day=18)
        cache = Mock()

        result = MonthPaymentBuilderSubscriptions.get_current_and_renewed_subscriptions(
            first_of_month=first_of_month, is_in_trial=False, cache=cache
        )

        self.assertEqual([], result)

        mock_get_all_subscriptions.assert_called_once_with(cache=cache)
        mock_get_subscriptions_that_will_be_renewed.assert_called_once_with(
            reference_date=first_of_month, cache=cache
        )
        mock_build_renewed_subscription.assert_called_once_with(
            subscription=original_subscription, cache=cache
        )
        mock_is_contract_in_trial.assert_called_once_with(
            contract=renewed_subscription,
            cache=cache,
            reference_date=first_of_month,
        )

    @patch.object(TrialPeriodManager, "is_contract_in_trial", autospec=True)
    @patch.object(
        AutomaticSubscriptionRenewalService, "build_renewed_subscription", autospec=True
    )
    @patch.object(
        AutomaticSubscriptionRenewalService,
        "get_subscriptions_that_will_be_renewed",
        autospec=True,
    )
    @patch.object(TapirCache, "get_all_subscriptions", autospec=True)
    def test_getCurrentAndRenewedSubscription_renewedSubscriptionFitsTrialParam_subscriptionReturned(
        self,
        mock_get_all_subscriptions: Mock,
        mock_get_subscriptions_that_will_be_renewed: Mock,
        mock_build_renewed_subscription: Mock,
        mock_is_contract_in_trial: Mock,
    ):
        original_subscription = SubscriptionFactory.build()
        renewed_subscription = SubscriptionFactory.build()
        mock_get_all_subscriptions.return_value = set()
        mock_get_subscriptions_that_will_be_renewed.return_value = {
            original_subscription
        }
        mock_build_renewed_subscription.return_value = renewed_subscription
        mock_is_contract_in_trial.return_value = False
        first_of_month = datetime.date(year=2025, month=9, day=18)
        cache = Mock()

        result = MonthPaymentBuilderSubscriptions.get_current_and_renewed_subscriptions(
            first_of_month=first_of_month, is_in_trial=False, cache=cache
        )

        self.assertEqual([renewed_subscription], result)

        mock_get_all_subscriptions.assert_called_once_with(cache=cache)
        mock_get_subscriptions_that_will_be_renewed.assert_called_once_with(
            reference_date=first_of_month, cache=cache
        )
        mock_build_renewed_subscription.assert_called_once_with(
            subscription=original_subscription, cache=cache
        )
        mock_is_contract_in_trial.assert_called_once_with(
            contract=renewed_subscription,
            cache=cache,
            reference_date=first_of_month,
        )
