import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager


class TestGetRenewedSubscriptionTrialDate(SimpleTestCase):
    @patch.object(TrialPeriodManager, "get_end_of_trial_period")
    def test_getRenewedSubscriptionTrialData_trialEndsBeforeEndOfPreviousSubscription_returnsTrialDisabledTrue(
        self, mock_get_end_of_trial_period: Mock
    ):
        subscription = Mock()
        end_of_subscription = datetime.date(year=2023, month=6, day=4)
        subscription.end_date = end_of_subscription

        end_of_trial = datetime.date(year=2023, month=6, day=3)
        mock_get_end_of_trial_period.return_value = end_of_trial

        trial_disabled, trial_end_date_override = (
            AutomaticSubscriptionRenewalService.get_renewed_subscription_trial_data(
                subscription
            )
        )

        self.assertTrue(trial_disabled)
        self.assertIsNone(trial_end_date_override)

    @patch.object(TrialPeriodManager, "get_end_of_trial_period")
    def test_getRenewedSubscriptionTrialData_trialEndsAfterEndOfPreviousSubscription_returnsTrialEndDate(
        self, mock_get_end_of_trial_period: Mock
    ):
        subscription = Mock()
        end_of_subscription = datetime.date(year=2023, month=6, day=4)
        subscription.end_date = end_of_subscription

        end_of_trial = datetime.date(year=2023, month=6, day=5)
        mock_get_end_of_trial_period.return_value = end_of_trial

        trial_disabled, trial_end_date_override = (
            AutomaticSubscriptionRenewalService.get_renewed_subscription_trial_data(
                subscription
            )
        )

        self.assertFalse(trial_disabled)
        self.assertEqual(end_of_trial, trial_end_date_override)
