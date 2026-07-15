import datetime
from unittest.mock import Mock, call, patch

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_delivery_charges import (
    MonthPaymentBuilderDeliveryCharges,
)
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PaymentFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBuildPaymentsForDeliveryCharges(TapirIntegrationTest):
    @patch.object(
        MemberPaymentRhythmService, "get_member_payment_rhythm", autospec=True
    )
    @patch.object(
        MonthPaymentBuilderUtils,
        "build_payment_for_contract_and_member",
        autospec=True,
    )
    @patch.object(
        MonthPaymentBuilderSubscriptions,
        "get_current_and_renewed_subscriptions",
        autospec=True,
    )
    def test_buildPaymentsForDeliveryCharges_notInTrial_callsBuildPaymentCorrectlyAndReturnsPayments(
        self,
        mock_get_current_and_renewed_subscriptions: Mock,
        mock_build_payment_for_contract_and_member: Mock,
        mock_get_member_payment_rhythm: Mock,
    ):
        members = MemberFactory.build_batch(size=3)
        member_one, member_two, member_three = members
        member_one.pk = "test_id_1"
        member_two.pk = "test_id_2"
        member_three.pk = "test_id_3"

        subscription_one = SubscriptionFactory.build(member=member_one)
        subscription_two_first = SubscriptionFactory.build(member=member_two)
        subscription_two_second = SubscriptionFactory.build(member=member_two)
        subscription_three = SubscriptionFactory.build(member=member_three)
        subscriptions_per_member = {
            member_one: {subscription_one},
            member_two: {subscription_two_first, subscription_two_second},
            member_three: {subscription_three},
        }

        mock_get_current_and_renewed_subscriptions.return_value = [
            subscription_one,
            subscription_two_first,
            subscription_two_second,
            subscription_three,
        ]

        rhythms = {
            member_one: MemberPaymentRhythm.Rhythm.MONTHLY,
            member_two: MemberPaymentRhythm.Rhythm.YEARLY,
            member_three: MemberPaymentRhythm.Rhythm.QUARTERLY,
        }
        mock_get_member_payment_rhythm.side_effect = (
            lambda member, reference_date, cache: rhythms[member]
        )

        payment_one = PaymentFactory.build()
        payment_two = PaymentFactory.build()
        payments = {
            member_one: payment_one,
            member_two: payment_two,
            member_three: None,
        }
        mock_build_payment_for_contract_and_member.side_effect = (
            lambda **kwargs: payments[kwargs["member"]]
        )

        cache = Mock()
        generated_payments = Mock()
        current_month = datetime.date(year=2026, month=5, day=1)

        result = MonthPaymentBuilderDeliveryCharges.build_payments_for_delivery_charges(
            current_month=current_month,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=False,
        )

        self.assertEqual({payment_one, payment_two}, set(result))

        mock_get_current_and_renewed_subscriptions.assert_called_once_with(
            cache=cache, first_of_month=current_month, is_in_trial=False
        )
        self.assertEqual(3, mock_get_member_payment_rhythm.call_count)
        self.assertEqual(3, mock_build_payment_for_contract_and_member.call_count)
        mock_build_payment_for_contract_and_member.assert_has_calls(
            [
                call(
                    member=member,
                    first_of_month=current_month,
                    contracts=subscriptions_per_member[member],
                    rhythm=rhythms[member],
                    cache=cache,
                    generated_payments=generated_payments,
                    in_trial=False,
                    payment_type=MonthPaymentBuilderDeliveryCharges.PAYMENT_TYPE_DELIVERY_CHARGE,
                    total_to_pay_function=MonthPaymentBuilderDeliveryCharges.get_total_to_pay,
                    allow_negative_amounts=True,
                )
                for member in members
            ],
            any_order=True,
        )

    @patch.object(
        MemberPaymentRhythmService, "get_member_payment_rhythm", autospec=True
    )
    @patch.object(
        MonthPaymentBuilderUtils,
        "build_payment_for_contract_and_member",
        autospec=True,
    )
    @patch.object(
        MonthPaymentBuilderSubscriptions,
        "get_current_and_renewed_subscriptions",
        autospec=True,
    )
    def test_buildPaymentsForDeliveryCharges_inTrial_usesMonthlyRhythmAndShiftedMonth(
        self,
        mock_get_current_and_renewed_subscriptions: Mock,
        mock_build_payment_for_contract_and_member: Mock,
        mock_get_member_payment_rhythm: Mock,
    ):
        member = MemberFactory.build()
        member.pk = "test_id_member"
        subscription = SubscriptionFactory.build(member=member)
        mock_get_current_and_renewed_subscriptions.return_value = [subscription]
        mock_build_payment_for_contract_and_member.return_value = None

        current_month = datetime.date(year=2026, month=5, day=1)
        target_month = datetime.date(year=2026, month=4, day=1)
        cache = Mock()
        generated_payments = Mock()

        MonthPaymentBuilderDeliveryCharges.build_payments_for_delivery_charges(
            current_month=current_month,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=True,
        )

        mock_get_current_and_renewed_subscriptions.assert_called_once_with(
            cache=cache, first_of_month=target_month, is_in_trial=True
        )
        mock_get_member_payment_rhythm.assert_not_called()
        mock_build_payment_for_contract_and_member.assert_called_once_with(
            member=member,
            first_of_month=target_month,
            contracts={subscription},
            rhythm=MemberPaymentRhythm.Rhythm.MONTHLY.value,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=True,
            payment_type=MonthPaymentBuilderDeliveryCharges.PAYMENT_TYPE_DELIVERY_CHARGE,
            total_to_pay_function=MonthPaymentBuilderDeliveryCharges.get_total_to_pay,
            allow_negative_amounts=True,
        )
