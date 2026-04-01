import datetime
from unittest.mock import patch, Mock, call

from django.test import SimpleTestCase

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)


class TestBuildPaymentForMonth(SimpleTestCase):
    @patch.object(
        MonthPaymentBuilderSolidarityContributions,
        "build_payments_for_solidarity_contributions",
    )
    @patch.object(MonthPaymentBuilderSubscriptions, "build_payments_for_subscriptions")
    def test_buildPaymentsForMonth_default_returnsPaymentsFromTrialAndNotTrialSubscriptions(
        self,
        mock_build_payments_for_subscriptions: Mock,
        mock_build_payments_for_solidarity_contributions: Mock,
    ):
        payment_1 = Mock()
        payment_2 = Mock()
        payment_3 = Mock()
        payment_4 = Mock()
        payment_5 = Mock()
        payment_6 = Mock()
        payment_7 = Mock()
        payment_8 = Mock()
        payment_9 = Mock()
        cache = Mock()
        generated_payments = {payment_6}

        subscriptions_trial_payments = [payment_1, payment_3]
        subscriptions_not_trial_payments = [payment_2, payment_4, payment_5]
        mock_build_payments_for_subscriptions.side_effect = (
            lambda current_month, cache, generated_payments, in_trial: (
                subscriptions_trial_payments
                if in_trial
                else subscriptions_not_trial_payments
            )
        )

        contribution_trial_payments = [payment_7, payment_8]
        contribution_not_trial_payments = [payment_9]
        mock_build_payments_for_solidarity_contributions.side_effect = (
            lambda current_month, cache, generated_payments, in_trial: (
                contribution_trial_payments
                if in_trial
                else contribution_not_trial_payments
            )
        )

        result = MonthPaymentBuilder.build_payments_for_month(
            reference_date=datetime.date(year=2022, month=5, day=12),
            cache=cache,
            generated_payments=generated_payments,
        )

        self.assertEqual(
            {
                payment_1,
                payment_2,
                payment_3,
                payment_4,
                payment_5,
                payment_7,
                payment_8,
                payment_9,
            },
            set(result),
        )
        self.assertEqual(2, mock_build_payments_for_subscriptions.call_count)
        mock_build_payments_for_subscriptions.assert_has_calls(
            [
                call(
                    current_month=datetime.date(year=2022, month=5, day=1),
                    cache=cache,
                    generated_payments=generated_payments,
                    in_trial=True,
                ),
                call(
                    current_month=datetime.date(year=2022, month=5, day=1),
                    cache=cache,
                    generated_payments={payment_6, payment_1, payment_3},
                    in_trial=False,
                ),
            ]
        )

        self.assertEqual(2, mock_build_payments_for_solidarity_contributions.call_count)
        mock_build_payments_for_solidarity_contributions.assert_has_calls(
            [
                call(
                    current_month=datetime.date(year=2022, month=5, day=1),
                    cache=cache,
                    generated_payments=generated_payments,
                    in_trial=True,
                ),
                call(
                    current_month=datetime.date(year=2022, month=5, day=1),
                    cache=cache,
                    generated_payments={payment_6, payment_7, payment_8},
                    in_trial=False,
                ),
            ]
        )
