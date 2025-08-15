import datetime
from unittest.mock import patch, Mock, call

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    MemberFactory,
    ProductTypeFactory,
    PaymentFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBuildPaymentsForSubscriptionsNotInTrial(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(
        MonthPaymentBuilder,
        "build_payment_for_subscriptions_for_member_and_product_type",
    )
    @patch.object(MemberPaymentRhythmService, "get_member_payment_rhythm")
    @patch.object(TrialPeriodManager, "is_subscription_in_trial")
    @patch.object(TapirCache, "get_all_subscriptions")
    def test_buildPaymentsForSubscriptionsNotInTrial_default_callsBuildPaymentCorrectlyAndReturnsPayments(
        self,
        mock_get_all_subscriptions: Mock,
        mock_is_subscription_in_trial: Mock,
        mock_get_member_payment_rhythm: Mock,
        mock_build_payment_for_subscriptions_for_member_and_product_type: Mock,
    ):
        member_1 = MemberFactory.create()
        member_2 = MemberFactory.create()
        product_type_1 = ProductTypeFactory.create()
        product_type_2 = ProductTypeFactory.create()

        subscription_in_trial = SubscriptionFactory.create(
            member=member_1, product__type=product_type_1
        )
        subscription_member_1_product_type_1_a = SubscriptionFactory.create(
            member=member_1, product__type=product_type_1
        )
        subscription_member_1_product_type_1_b = SubscriptionFactory.create(
            member=member_1, product__type=product_type_1
        )
        subscription_member_1_product_type_2 = SubscriptionFactory.create(
            member=member_1, product__type=product_type_2
        )
        subscription_member_2_product_type_1 = SubscriptionFactory.create(
            member=member_2, product__type=product_type_1
        )

        mock_get_all_subscriptions.return_value = {
            subscription_in_trial,
            subscription_member_1_product_type_1_a,
            subscription_member_1_product_type_1_b,
            subscription_member_1_product_type_2,
            subscription_member_2_product_type_1,
        }

        mock_is_subscription_in_trial.side_effect = (
            lambda subscription, reference_date, cache: subscription
            == subscription_in_trial
        )
        mock_get_member_payment_rhythm.side_effect = (
            lambda member, reference_date, cache: (
                MemberPaymentRhythm.Rhythm.MONTHLY
                if member == member_1
                else MemberPaymentRhythm.Rhythm.QUARTERLY
            )
        )

        mock_build_payment_for_subscriptions_for_member_and_product_type.side_effect = (
            lambda member, first_of_month, subscriptions, product_type, rhythm, cache: (
                None
                if subscription_member_1_product_type_2 in subscriptions
                else PaymentFactory.create(
                    mandate_ref__member=member, type=product_type.name
                )
            )
        )

        current_month = datetime.date(year=2027, month=6, day=1)
        cache = Mock()

        payments = MonthPaymentBuilder.build_payments_for_subscriptions_not_in_trial(
            current_month=current_month, cache=cache
        )

        # There should be 2 payments: one for [subscription_member_1_product_type_1_A, subscription_member_1_product_type_1_B,]
        # one for [subscription_member_2_product_type_1]
        self.assertEqual(2, len(payments))
        self.assertEqual(product_type_1.name, payments[0].type)
        self.assertEqual(product_type_1.name, payments[1].type)
        self.assertEqual(
            {member_1, member_2},
            set([payment.mandate_ref.member for payment in payments]),
        )

        self.assertEqual(
            3,
            mock_build_payment_for_subscriptions_for_member_and_product_type.call_count,
        )
        mock_build_payment_for_subscriptions_for_member_and_product_type.assert_has_calls(
            [
                call(
                    member=member_1,
                    first_of_month=current_month,
                    subscriptions={
                        subscription_member_1_product_type_1_a,
                        subscription_member_1_product_type_1_b,
                    },
                    product_type=product_type_1,
                    rhythm=MemberPaymentRhythm.Rhythm.MONTHLY,
                    cache=cache,
                ),
                call(
                    member=member_1,
                    first_of_month=current_month,
                    subscriptions={subscription_member_1_product_type_2},
                    product_type=product_type_2,
                    rhythm=MemberPaymentRhythm.Rhythm.MONTHLY,
                    cache=cache,
                ),
                call(
                    member=member_2,
                    first_of_month=current_month,
                    subscriptions={subscription_member_2_product_type_1},
                    product_type=product_type_1,
                    rhythm=MemberPaymentRhythm.Rhythm.QUARTERLY,
                    cache=cache,
                ),
            ],
            any_order=True,
        )
