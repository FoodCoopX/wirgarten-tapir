import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder


class TestBuildPaymentForMonth(SimpleTestCase):
    @patch.object(MonthPaymentBuilder, "build_payments_for_subscriptions_not_in_trial")
    @patch.object(MonthPaymentBuilder, "build_payments_for_subscriptions_in_trial")
    def test_buildPaymentsForMonth_default_returnsPaymentsFromTrialAndNotTrialSubscriptions(
        self,
        mock_build_payments_for_subscriptions_in_trial: Mock,
        mock_build_payments_for_subscriptions_not_in_trial: Mock,
    ):
        payment_1 = Mock()
        payment_2 = Mock()
        payment_3 = Mock()
        payment_4 = Mock()
        payment_5 = Mock()
        payment_6 = Mock()
        cache = Mock()
        generated_payments = {payment_6}

        mock_build_payments_for_subscriptions_in_trial.return_value = [
            payment_1,
            payment_3,
        ]
        mock_build_payments_for_subscriptions_not_in_trial.return_value = [
            payment_2,
            payment_4,
            payment_5,
        ]

        result = MonthPaymentBuilder.build_payments_for_month(
            reference_date=datetime.date(year=2022, month=5, day=12),
            cache=cache,
            generated_payments=generated_payments,
        )

        self.assertEqual(
            {payment_1, payment_2, payment_3, payment_4, payment_5}, set(result)
        )
        mock_build_payments_for_subscriptions_in_trial.assert_called_once_with(
            current_month=datetime.date(year=2022, month=5, day=1),
            cache=cache,
            generated_payments=generated_payments,
        )
        mock_build_payments_for_subscriptions_not_in_trial.assert_called_once_with(
            current_month=datetime.date(year=2022, month=5, day=1),
            cache=cache,
            generated_payments={payment_6, payment_1, payment_3},
        )
