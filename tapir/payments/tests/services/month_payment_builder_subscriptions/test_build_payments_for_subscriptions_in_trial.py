import datetime
from unittest.mock import patch, Mock, call

from tapir.payments.models import MemberPaymentRhythm
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


class TestBuildPaymentsForSubscriptionsInTrial(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(
        MonthPaymentBuilderUtils,
        "build_payment_for_contract_and_member",
    )
    @patch.object(
        MonthPaymentBuilderSubscriptions, "get_current_and_renewed_subscriptions"
    )
    def test_buildPaymentsForSubscriptionsInTrial_default_callsBuildPaymentCorrectlyAndReturnsPayments(
        self,
        mock_get_current_and_renewed_subscriptions: Mock,
        mock_build_payment_for_contract_and_member: Mock,
    ):
        member_1 = MemberFactory.create(first_name="M1")
        member_2 = MemberFactory.create(first_name="M2")
        product_type_1 = ProductTypeFactory.create(name="PT1")
        product_type_2 = ProductTypeFactory.create(name="PT2")

        subscription_member_1_product_type_1_a = SubscriptionFactory.create(
            member=member_1, product__type=product_type_1, product__name="P1"
        )
        subscription_member_1_product_type_1_b = SubscriptionFactory.create(
            member=member_1, product__type=product_type_1, product__name="P2"
        )
        subscription_member_1_product_type_2 = SubscriptionFactory.create(
            member=member_1, product__type=product_type_2, product__name="P3"
        )
        subscription_member_2_product_type_1 = SubscriptionFactory.create(
            member=member_2, product__type=product_type_1, product__name="P4"
        )

        mock_get_current_and_renewed_subscriptions.return_value = {
            subscription_member_1_product_type_1_a,
            subscription_member_1_product_type_1_b,
            subscription_member_1_product_type_2,
            subscription_member_2_product_type_1,
        }

        mock_build_payment_for_contract_and_member.side_effect = lambda **kwargs: (
            None
            if subscription_member_1_product_type_2 in kwargs["contracts"]
            else PaymentFactory.build(
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
            in_trial=True,
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
        previous_month = datetime.date(year=2027, month=5, day=1)
        mock_build_payment_for_contract_and_member.assert_has_calls(
            [
                call(
                    member=member_1,
                    first_of_month=previous_month,
                    contracts={
                        subscription_member_1_product_type_1_a,
                        subscription_member_1_product_type_1_b,
                    },
                    payment_type=product_type_1.name,
                    rhythm=MemberPaymentRhythm.Rhythm.MONTHLY,
                    cache=cache,
                    generated_payments=generated_payments,
                    in_trial=True,
                    total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
                    allow_negative_amounts=False,
                ),
                call(
                    member=member_1,
                    first_of_month=previous_month,
                    contracts={subscription_member_1_product_type_2},
                    payment_type=product_type_2.name,
                    rhythm=MemberPaymentRhythm.Rhythm.MONTHLY,
                    cache=cache,
                    generated_payments=generated_payments,
                    in_trial=True,
                    total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
                    allow_negative_amounts=False,
                ),
                call(
                    member=member_2,
                    first_of_month=previous_month,
                    contracts={subscription_member_2_product_type_1},
                    payment_type=product_type_1.name,
                    rhythm=MemberPaymentRhythm.Rhythm.MONTHLY,
                    cache=cache,
                    generated_payments=generated_payments,
                    in_trial=True,
                    total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
                    allow_negative_amounts=False,
                ),
            ],
            any_order=True,
        )
