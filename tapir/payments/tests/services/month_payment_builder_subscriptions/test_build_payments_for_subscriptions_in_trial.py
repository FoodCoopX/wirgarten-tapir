import datetime
from decimal import Decimal
from unittest.mock import patch, Mock, call

from django.urls import reverse
from rest_framework import status

from tapir.payments.models import MemberPaymentRhythm, MemberCredit
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.payments.tasks import create_payments_for_this_month
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import Payment, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    MemberFactory,
    ProductTypeFactory,
    PaymentFactory,
    GrowingPeriodFactory,
    ProductPriceFactory,
    ProductFactory,
    ProductCapacityFactory,
    MemberPickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


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

    @patch.object(
        ContractStartDateCalculator,
        "get_next_contract_start_date_in_growing_period",
        autospec=True,
    )
    def test_buildPaymentsForSubscriptionsInTrial_subscriptionReducedAfterPaymentWasPersisted_correctCreditCreatedAndNoNewPayment(
        self, mock_get_next_contract_start_date_in_growing_period: Mock
    ):
        # This is a regression test for infra#87, in particular this case:
        # https://github.com/FoodCoopX/infra/issues/87#issuecomment-4612988509
        # It is the equivalent of test_buildPaymentsForSolidarityContribution_contributionReduceAfterPaymentWasPersisted_noNegativePaymentCreated

        mock_timezone(test=self, now=datetime.datetime(year=2020, month=5, day=15))
        member = MemberFactory.create()
        self._set_parameter(key=ParameterKeys.TRIAL_PERIOD_ENABLED, value=False)
        self._set_parameter(
            key=ParameterKeys.PAYMENT_START_DATE,
            value=datetime.date(year=2020, month=1, day=1),
        )

        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=1, day=1)
        )
        old_subscription = SubscriptionFactory.create(
            period=growing_period,
            member=member,
            quantity=1,
            product__type__delivery_cycle=WEEKLY[0],
        )
        MemberPickupLocationFactory.create(
            member=member, valid_from=growing_period.start_date
        )
        ProductCapacityFactory.create(
            period=growing_period,
            product_type=old_subscription.product.type,
            capacity=1000,
        )
        MemberPaymentRhythm.objects.create(
            member=member,
            rhythm=MemberPaymentRhythm.Rhythm.YEARLY,
            valid_from=growing_period.start_date,
        )
        ProductPriceFactory.create(
            product=old_subscription.product,
            price=10,
            valid_from=growing_period.start_date,
        )

        create_payments_for_this_month(reference_date=growing_period.start_date)
        payment = Payment.objects.get()
        self.assertEqual(member, payment.mandate_ref.member)
        self.assertEqual(Decimal("120.00"), payment.amount)

        smaller_product = ProductFactory.create(type=old_subscription.product.type)
        ProductPriceFactory.create(
            product=smaller_product, price=5, valid_from=growing_period.start_date
        )
        mock_get_next_contract_start_date_in_growing_period.return_value = (
            datetime.date(year=2020, month=7, day=1)
        )

        self.client.force_login(MemberFactory.create(is_superuser=True))
        response = self.client.post(
            reverse(
                "subscriptions:update_subscription",
            ),
            data={
                "member_id": member.id,
                "product_type_id": old_subscription.product.type.id,
                "shopping_cart": {smaller_product.id: 1},
                "sepa_allowed": True,
                "cancellation_policy_read": True,
                "growing_period_id": growing_period.id,
                "account_owner": "test account owner",
                "iban": "NL21RABO7007935591",
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())

        old_subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2020, month=6, day=30), old_subscription.end_date
        )
        new_subscription = Subscription.objects.order_by("start_date").last()
        self.assertEqual(
            datetime.date(year=2020, month=7, day=1), new_subscription.start_date
        )
        credit = MemberCredit.objects.get()
        self.assertEqual(Decimal("30.00"), credit.amount)

        result = MonthPaymentBuilderSubscriptions.build_payments_for_subscriptions(
            current_month=datetime.date(year=2020, month=7, day=1),
            cache={},
            generated_payments=set(),
            in_trial=False,
        )

        self.assertEqual(0, len(result))

    @patch.object(
        ContractStartDateCalculator,
        "get_next_contract_start_date_in_growing_period",
        autospec=True,
    )
    def test_buildPaymentsForSubscriptionsInTrial_subscriptionAddedAfterAPause_correctFuturePaymentCreated(
        self, mock_get_next_contract_start_date_in_growing_period: Mock
    ):
        # This is a regression test for infra#87, in particular this case:
        # A member has a subscription and a yearly payment rhythm,
        # but the subscription is "force canceled" to end in the middle of the year.
        # Later in the same growing period, the member subscribes to another subscription
        # Payments and credits must be correct at all steps

        mock_timezone(test=self, now=datetime.datetime(year=2020, month=5, day=15))
        member = MemberFactory.create()
        self._set_parameter(key=ParameterKeys.TRIAL_PERIOD_ENABLED, value=False)
        self._set_parameter(
            key=ParameterKeys.PAYMENT_START_DATE,
            value=datetime.date(year=2020, month=1, day=1),
        )

        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=1, day=1)
        )
        old_subscription = SubscriptionFactory.create(
            period=growing_period,
            member=member,
            quantity=1,
            product__type__delivery_cycle=WEEKLY[0],
        )
        MemberPickupLocationFactory.create(
            member=member, valid_from=growing_period.start_date
        )
        ProductCapacityFactory.create(
            period=growing_period,
            product_type=old_subscription.product.type,
            capacity=1000,
        )
        MemberPaymentRhythm.objects.create(
            member=member,
            rhythm=MemberPaymentRhythm.Rhythm.YEARLY,
            valid_from=growing_period.start_date,
        )
        ProductPriceFactory.create(
            product=old_subscription.product,
            price=10,
            valid_from=growing_period.start_date,
        )

        create_payments_for_this_month(reference_date=growing_period.start_date)
        payment = Payment.objects.get()
        self.assertEqual(member, payment.mandate_ref.member)
        self.assertEqual(Decimal("120.00"), payment.amount)

        self.client.force_login(MemberFactory.create(is_superuser=True))
        response = self.client.post(
            reverse(
                "subscriptions:dates_change",
            ),
            data={
                "start_date_is_on_period_start": True,
                "end_date_is_on_period_end": False,
                "start_week": -1,
                "end_week": 22,
                "subscription_id": old_subscription.id,
                "update_end_date_of_other_contracts": False,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())

        old_subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2020, month=5, day=31), old_subscription.end_date
        )
        credit = MemberCredit.objects.get()
        self.assertEqual(Decimal("70.00"), credit.amount)

        result = MonthPaymentBuilderSubscriptions.build_payments_for_subscriptions(
            current_month=datetime.date(year=2020, month=6, day=1),
            cache={},
            generated_payments=set(),
            in_trial=False,
        )

        self.assertEqual(0, len(result))

        other_product = ProductFactory.create(type=old_subscription.product.type)
        ProductPriceFactory.create(
            product=other_product, price=5, valid_from=growing_period.start_date
        )
        mock_get_next_contract_start_date_in_growing_period.return_value = (
            datetime.date(year=2020, month=7, day=1)
        )

        self.client.force_login(MemberFactory.create(is_superuser=True))
        response = self.client.post(
            reverse(
                "subscriptions:update_subscription",
            ),
            data={
                "member_id": member.id,
                "product_type_id": old_subscription.product.type.id,
                "shopping_cart": {other_product.id: 1},
                "sepa_allowed": True,
                "cancellation_policy_read": True,
                "growing_period_id": growing_period.id,
                "account_owner": "test account owner",
                "iban": "NL21RABO7007935591",
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())
        self.assertEqual(1, MemberCredit.objects.count())

        new_subscription = Subscription.objects.order_by("start_date").last()
        self.assertEqual(
            datetime.date(year=2020, month=7, day=1), new_subscription.start_date
        )

        result = MonthPaymentBuilderSubscriptions.build_payments_for_subscriptions(
            current_month=datetime.date(year=2020, month=7, day=1),
            cache={},
            generated_payments=set(),
            in_trial=False,
        )

        self.assertEqual(1, len(result))
        self.assertEqual(member, result[0].mandate_ref.member)
        self.assertEqual(Decimal("30.00"), result[0].amount)
