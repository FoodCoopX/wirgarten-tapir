import datetime
from unittest.mock import Mock, call, patch

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_delivery_charges import (
    MissingPickupLocationError,
    MonthPaymentBuilderDeliveryCharges,
)
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.payments.tests.factories import MemberCreditFactory
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
        MonthPaymentBuilderDeliveryCharges,
        "build_payments_for_member",
        autospec=True,
    )
    @patch.object(
        MonthPaymentBuilderSubscriptions,
        "get_current_and_renewed_subscriptions_ignoring_trial_state",
        autospec=True,
    )
    def test_buildPaymentsForDeliveryCharges_default_billsEachMemberOnceAtRealRhythmAndReturnsArtifacts(
        self,
        mock_get_subscriptions: Mock,
        mock_build_payments_for_member: Mock,
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

        mock_get_subscriptions.return_value = {
            subscription_one,
            subscription_two_first,
            subscription_two_second,
            subscription_three,
        }

        rhythms = {
            member_one: MemberPaymentRhythm.Rhythm.MONTHLY,
            member_two: MemberPaymentRhythm.Rhythm.YEARLY,
            member_three: MemberPaymentRhythm.Rhythm.QUARTERLY,
        }
        mock_get_member_payment_rhythm.side_effect = (
            lambda member, reference_date, cache: rhythms[member]
        )

        payment_one = PaymentFactory.build()
        payment_two_first = PaymentFactory.build()
        payment_two_second = PaymentFactory.build()
        credit_one = MemberCreditFactory.build()
        credit_three = MemberCreditFactory.build()
        artifacts_per_member = {
            member_one: ([payment_one], [credit_one]),
            member_two: ([payment_two_first, payment_two_second], []),
            member_three: ([], [credit_three]),
        }
        mock_build_payments_for_member.side_effect = (
            lambda **kwargs: artifacts_per_member[kwargs["member"]]
        )

        cache = Mock()
        generated_payments = Mock()
        generated_credits = Mock()
        current_month = datetime.date(year=2026, month=5, day=1)

        payments, credits = (
            MonthPaymentBuilderDeliveryCharges.build_payments_for_delivery_charges(
                current_month=current_month,
                cache=cache,
                generated_payments=generated_payments,
                generated_credits=generated_credits,
            )
        )

        self.assertEqual(
            {payment_one, payment_two_first, payment_two_second}, set(payments)
        )
        self.assertEqual({credit_one, credit_three}, set(credits))

        mock_get_subscriptions.assert_called_once_with(
            cache=cache, first_of_month=current_month
        )
        self.assertEqual(3, mock_get_member_payment_rhythm.call_count)
        mock_get_member_payment_rhythm.assert_has_calls(
            [
                call(member=member, reference_date=current_month, cache=cache)
                for member in members
            ],
            any_order=True,
        )
        self.assertEqual(3, mock_build_payments_for_member.call_count)
        mock_build_payments_for_member.assert_has_calls(
            [
                call(
                    member=member,
                    contracts=subscriptions_per_member[member],
                    first_of_month=current_month,
                    rhythm=rhythms[member],
                    cache=cache,
                    generated_payments=generated_payments,
                    generated_credits=generated_credits,
                )
                for member in members
            ],
            any_order=True,
        )

    @patch.object(
        MemberPaymentRhythmService, "get_member_payment_rhythm", autospec=True
    )
    @patch.object(
        MonthPaymentBuilderDeliveryCharges,
        "build_payments_for_member",
        autospec=True,
    )
    @patch.object(
        MonthPaymentBuilderSubscriptions,
        "get_current_and_renewed_subscriptions_ignoring_trial_state",
        autospec=True,
    )
    def test_buildPaymentsForDeliveryCharges_memberMissesPickupLocation_raisesAndAbortsTheRun(
        self,
        mock_get_subscriptions: Mock,
        mock_build_payments_for_member: Mock,
        mock_get_member_payment_rhythm: Mock,
    ):
        member_ok, member_broken = MemberFactory.build_batch(size=2)
        member_ok.pk = "member_ok"
        member_broken.pk = "member_broken"
        subscription_ok = SubscriptionFactory.build(member=member_ok)
        subscription_broken = SubscriptionFactory.build(member=member_broken)
        mock_get_subscriptions.return_value = {subscription_ok, subscription_broken}
        mock_get_member_payment_rhythm.return_value = MemberPaymentRhythm.Rhythm.MONTHLY

        payment_ok = PaymentFactory.build()

        def side_effect(**kwargs):
            if kwargs["member"] is member_broken:
                raise MissingPickupLocationError("no pickup location")
            return [payment_ok], []

        mock_build_payments_for_member.side_effect = side_effect

        with self.assertRaises(MissingPickupLocationError):
            MonthPaymentBuilderDeliveryCharges.build_payments_for_delivery_charges(
                current_month=datetime.date(year=2026, month=5, day=1),
                cache=Mock(),
                generated_payments=Mock(),
                generated_credits=Mock(),
            )
