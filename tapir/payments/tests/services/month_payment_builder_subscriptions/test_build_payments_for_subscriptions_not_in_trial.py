import datetime
from unittest.mock import patch, Mock, call

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
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
        MonthPaymentBuilderUtils,
        "build_payment_for_contract_and_member",
    )
    @patch.object(MemberPaymentRhythmService, "get_member_payment_rhythm")
    @patch.object(
        MonthPaymentBuilderSubscriptions, "get_current_and_renewed_subscriptions"
    )
    def test_buildPaymentsForSubscriptionsNotInTrial_default_callsBuildPaymentCorrectlyAndReturnsPayments(
        self,
        mock_get_current_and_renewed_subscriptions: Mock,
        mock_get_member_payment_rhythm: Mock,
        mock_build_payment_for_contract_and_member: Mock,
    ):
        member_1 = MemberFactory.create()
        member_2 = MemberFactory.create()
        product_type_1 = ProductTypeFactory.create()
        product_type_2 = ProductTypeFactory.create()

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

        mock_get_current_and_renewed_subscriptions.return_value = {
            subscription_member_1_product_type_1_a,
            subscription_member_1_product_type_1_b,
            subscription_member_1_product_type_2,
            subscription_member_2_product_type_1,
        }

        mock_get_member_payment_rhythm.side_effect = (
            lambda member, reference_date, cache: (
                MemberPaymentRhythm.Rhythm.MONTHLY
                if member == member_1
                else MemberPaymentRhythm.Rhythm.QUARTERLY
            )
        )

        mock_build_payment_for_contract_and_member.side_effect = lambda **kwargs: (
            None
            if subscription_member_1_product_type_2 in kwargs["contracts"]
            else PaymentFactory.create(
                mandate_ref__member=kwargs["member"], type=kwargs["payment_type"]
            )
        )

        current_month = datetime.date(year=2027, month=6, day=1)
        cache = Mock()
        generated_payments = Mock()

        payments = MonthPaymentBuilderSubscriptions.build_payments_for_subscriptions(
            current_month=current_month,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=False,
        )

        # There should be 2 payments: one for [subscription_member_1_product_type_1_A, subscription_member_1_product_type_1_B,]
        # one for [subscription_member_2_product_type_1]
        self.assertEqual(2, len(payments))
        self.assertEqual(product_type_1.name, payments[0].type)
        self.assertEqual(product_type_1.name, payments[1].type)
        self.assertEqual(
            {member_1, member_2},
            {payment.mandate_ref.member for payment in payments},
        )

        self.assertEqual(
            3,
            mock_build_payment_for_contract_and_member.call_count,
        )
        mock_build_payment_for_contract_and_member.assert_has_calls(
            [
                call(
                    member=member_1,
                    first_of_month=current_month,
                    contracts={
                        subscription_member_1_product_type_1_a,
                        subscription_member_1_product_type_1_b,
                    },
                    payment_type=product_type_1.name,
                    rhythm=MemberPaymentRhythm.Rhythm.MONTHLY,
                    cache=cache,
                    generated_payments=generated_payments,
                    in_trial=False,
                    total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
                    allow_negative_amounts=False,
                ),
                call(
                    member=member_1,
                    first_of_month=current_month,
                    contracts={subscription_member_1_product_type_2},
                    payment_type=product_type_2.name,
                    rhythm=MemberPaymentRhythm.Rhythm.MONTHLY,
                    cache=cache,
                    generated_payments=generated_payments,
                    in_trial=False,
                    total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
                    allow_negative_amounts=False,
                ),
                call(
                    member=member_2,
                    first_of_month=current_month,
                    contracts={subscription_member_2_product_type_1},
                    payment_type=product_type_1.name,
                    rhythm=MemberPaymentRhythm.Rhythm.QUARTERLY,
                    cache=cache,
                    generated_payments=generated_payments,
                    in_trial=False,
                    total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
                    allow_negative_amounts=False,
                ),
            ],
            any_order=True,
        )
