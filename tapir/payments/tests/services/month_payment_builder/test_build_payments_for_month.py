import datetime
from unittest.mock import patch, Mock, call

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.payments.services.month_payment_builder_association_membership import (
    MonthPaymentBuilderAssociationMembership,
)
from tapir.payments.services.month_payment_builder_delivery_charges import (
    MonthPaymentBuilderDeliveryCharges,
)
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildPaymentForMonth(TapirUnitTest):
    @patch.object(
        MonthPaymentBuilderDeliveryCharges,
        "build_payments_for_delivery_charges",
        autospec=True,
    )
    @patch.object(
        MonthPaymentBuilderAssociationMembership,
        "build_payments_for_association_memberships",
        autospec=True,
    )
    @patch.object(
        MonthPaymentBuilderSolidarityContributions,
        "build_payments_for_solidarity_contributions",
        autospec=True,
    )
    @patch.object(
        MonthPaymentBuilderSubscriptions,
        "build_payments_for_subscriptions",
        autospec=True,
    )
    def test_buildPaymentsForMonth_default_returnsPaymentsFromAllBuilders(
        self,
        mock_build_payments_for_subscriptions: Mock,
        mock_build_payments_for_solidarity_contributions: Mock,
        mock_build_payments_for_association_memberships: Mock,
        mock_build_payments_for_delivery_charges: Mock,
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
        payment_10 = Mock()
        payment_12 = Mock()
        payment_13 = Mock()
        credit_1 = Mock()
        cache = Mock()
        generated_payments = {payment_6}
        generated_credits = set()

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

        membership_payments = [payment_12, payment_13]
        mock_build_payments_for_association_memberships.return_value = (
            membership_payments
        )

        delivery_charge_payments = [payment_10]
        delivery_charge_credits = [credit_1]
        mock_build_payments_for_delivery_charges.return_value = (
            delivery_charge_payments,
            delivery_charge_credits,
        )

        payments, credits = MonthPaymentBuilder.build_payments_for_month(
            reference_date=datetime.date(year=2022, month=5, day=12),
            cache=cache,
            generated_payments=generated_payments,
            generated_credits=generated_credits,
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
                payment_10,
                payment_12,
                payment_13,
            },
            set(payments),
        )
        self.assertEqual({credit_1}, set(credits))
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

        mock_build_payments_for_association_memberships.assert_called_once_with(
            current_month=datetime.date(year=2022, month=5, day=1),
            cache=cache,
            generated_payments=generated_payments,
        )

        mock_build_payments_for_delivery_charges.assert_called_once_with(
            current_month=datetime.date(year=2022, month=5, day=1),
            cache=cache,
            generated_payments=generated_payments,
            generated_credits=generated_credits,
        )
