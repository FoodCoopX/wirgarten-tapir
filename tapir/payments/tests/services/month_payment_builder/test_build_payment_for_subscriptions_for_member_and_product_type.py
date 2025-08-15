import datetime
from decimal import Decimal
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.wirgarten.models import Payment
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    MandateReferenceFactory,
    ProductTypeFactory,
)


class TestBuildPaymentForSubscriptionsForMemberAndProductType(SimpleTestCase):
    @patch.object(MonthPaymentBuilder, "get_payment_due_date_on_month")
    @patch.object(MonthPaymentBuilder, "get_total_to_pay")
    @patch.object(MonthPaymentBuilder, "get_already_paid_amount")
    @patch("tapir.payments.services.month_payment_builder.get_or_create_mandate_ref")
    @patch.object(MemberPaymentRhythmService, "get_last_day_of_rhythm_period")
    @patch.object(MemberPaymentRhythmService, "get_first_day_of_rhythm_period")
    def test_buildPaymentForSubscriptionsForMemberAndProductType_totalToPayIsMoreThanAlreadyPaid_returnsPaymentWithDifference(
        self,
        mock_get_first_day_of_rhythm_period: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
        mock_get_or_create_mandate_ref: Mock,
        mock_get_already_paid_amount: Mock,
        mock_get_total_to_pay: Mock,
        mock_get_payment_due_date_on_month: Mock,
    ):
        range_start = datetime.date(year=2026, month=7, day=1)
        mock_get_first_day_of_rhythm_period.return_value = range_start
        range_end = datetime.date(year=2026, month=7, day=31)
        mock_get_last_day_of_rhythm_period.return_value = range_end
        member = MemberFactory.build()
        mandate_ref = MandateReferenceFactory.build(member=member, ref="test_ref")
        mock_get_or_create_mandate_ref.return_value = mandate_ref
        mock_get_already_paid_amount.return_value = 10
        mock_get_total_to_pay.return_value = 17.5
        due_date = datetime.date(year=2026, month=7, day=13)
        mock_get_payment_due_date_on_month.return_value = due_date

        first_of_month = Mock()
        product_type = ProductTypeFactory.build(name="pt_test_name")
        subscriptions = SubscriptionFactory.build_batch(
            size=3, product__type=product_type, member=member, mandate_ref=mandate_ref
        )
        rhythm = Mock()
        cache = Mock()

        payment = MonthPaymentBuilder.build_payment_for_subscriptions_for_member_and_product_type(
            member=member,
            first_of_month=first_of_month,
            subscriptions=subscriptions,
            product_type=product_type,
            rhythm=rhythm,
            cache=cache,
        )

        self.assertIsNotNone(
            payment, "Payment should have been built since there is 7.5 left to pay"
        )
        self.assertEqual(due_date, payment.due_date)
        self.assertEqual(Decimal(7.5), payment.amount)
        self.assertEqual(mandate_ref, payment.mandate_ref)
        self.assertEqual(Payment.PaymentStatus.DUE, payment.status)
        self.assertEqual("pt_test_name", payment.type)
        self.assertEqual(range_start, payment.subscription_payment_range_start)
        self.assertEqual(range_end, payment.subscription_payment_range_end)

        mock_get_first_day_of_rhythm_period.assert_called_once_with(
            rhythm=rhythm, reference_date=first_of_month, cache=cache
        )
        mock_get_last_day_of_rhythm_period.assert_called_once_with(
            rhythm=rhythm, reference_date=first_of_month, cache=cache
        )
        mock_get_or_create_mandate_ref.assert_called_once_with(
            member=member, cache=cache
        )
        mock_get_already_paid_amount.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            product_type_name="pt_test_name",
        )
        mock_get_total_to_pay.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            subscriptions=subscriptions,
            cache=cache,
        )
        mock_get_payment_due_date_on_month.assert_called_once_with(
            reference_date=first_of_month, cache=cache
        )

    @patch.object(MonthPaymentBuilder, "get_payment_due_date_on_month")
    @patch.object(MonthPaymentBuilder, "get_total_to_pay")
    @patch.object(MonthPaymentBuilder, "get_already_paid_amount")
    @patch("tapir.payments.services.month_payment_builder.get_or_create_mandate_ref")
    @patch.object(MemberPaymentRhythmService, "get_last_day_of_rhythm_period")
    @patch.object(MemberPaymentRhythmService, "get_first_day_of_rhythm_period")
    def test_buildPaymentForSubscriptionsForMemberAndProductType_totalToPayIsEqualToAlreadyPaid_returnsNone(
        self,
        mock_get_first_day_of_rhythm_period: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
        mock_get_or_create_mandate_ref: Mock,
        mock_get_already_paid_amount: Mock,
        mock_get_total_to_pay: Mock,
        mock_get_payment_due_date_on_month: Mock,
    ):
        range_start = datetime.date(year=2026, month=7, day=1)
        mock_get_first_day_of_rhythm_period.return_value = range_start
        range_end = datetime.date(year=2026, month=7, day=31)
        mock_get_last_day_of_rhythm_period.return_value = range_end
        member = MemberFactory.build()
        mandate_ref = MandateReferenceFactory.build(member=member, ref="test_ref")
        mock_get_or_create_mandate_ref.return_value = mandate_ref
        mock_get_already_paid_amount.return_value = 17.5
        mock_get_total_to_pay.return_value = 17.5

        first_of_month = Mock()
        product_type = ProductTypeFactory.build(name="pt_test_name")
        subscriptions = SubscriptionFactory.build_batch(
            size=3, product__type=product_type, member=member, mandate_ref=mandate_ref
        )
        rhythm = Mock()
        cache = Mock()

        payment = MonthPaymentBuilder.build_payment_for_subscriptions_for_member_and_product_type(
            member=member,
            first_of_month=first_of_month,
            subscriptions=subscriptions,
            product_type=product_type,
            rhythm=rhythm,
            cache=cache,
        )

        self.assertIsNone(
            payment,
            "Payment should not have been built since the 17.5 are already paid",
        )

        mock_get_first_day_of_rhythm_period.assert_called_once_with(
            rhythm=rhythm, reference_date=first_of_month, cache=cache
        )
        mock_get_last_day_of_rhythm_period.assert_called_once_with(
            rhythm=rhythm, reference_date=first_of_month, cache=cache
        )
        mock_get_or_create_mandate_ref.assert_called_once_with(
            member=member, cache=cache
        )
        mock_get_already_paid_amount.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            product_type_name="pt_test_name",
        )
        mock_get_total_to_pay.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            subscriptions=subscriptions,
            cache=cache,
        )
        mock_get_payment_due_date_on_month.assert_not_called()

    @patch.object(MonthPaymentBuilder, "get_payment_due_date_on_month")
    @patch.object(MonthPaymentBuilder, "get_total_to_pay")
    @patch.object(MonthPaymentBuilder, "get_already_paid_amount")
    @patch("tapir.payments.services.month_payment_builder.get_or_create_mandate_ref")
    @patch.object(MemberPaymentRhythmService, "get_last_day_of_rhythm_period")
    @patch.object(MemberPaymentRhythmService, "get_first_day_of_rhythm_period")
    def test_buildPaymentForSubscriptionsForMemberAndProductType_totalToPayIsLessThanAlreadyPaid_returnsNone(
        self,
        mock_get_first_day_of_rhythm_period: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
        mock_get_or_create_mandate_ref: Mock,
        mock_get_already_paid_amount: Mock,
        mock_get_total_to_pay: Mock,
        mock_get_payment_due_date_on_month: Mock,
    ):
        range_start = datetime.date(year=2026, month=7, day=1)
        mock_get_first_day_of_rhythm_period.return_value = range_start
        range_end = datetime.date(year=2026, month=7, day=31)
        mock_get_last_day_of_rhythm_period.return_value = range_end
        member = MemberFactory.build()
        mandate_ref = MandateReferenceFactory.build(member=member, ref="test_ref")
        mock_get_or_create_mandate_ref.return_value = mandate_ref
        mock_get_already_paid_amount.return_value = 20
        mock_get_total_to_pay.return_value = 17.5

        first_of_month = Mock()
        product_type = ProductTypeFactory.build(name="pt_test_name")
        subscriptions = SubscriptionFactory.build_batch(
            size=3, product__type=product_type, member=member, mandate_ref=mandate_ref
        )
        rhythm = Mock()
        cache = Mock()

        payment = MonthPaymentBuilder.build_payment_for_subscriptions_for_member_and_product_type(
            member=member,
            first_of_month=first_of_month,
            subscriptions=subscriptions,
            product_type=product_type,
            rhythm=rhythm,
            cache=cache,
        )

        self.assertIsNone(
            payment,
            "Payment should not have been built since more than enough has already been paid",
        )

        mock_get_first_day_of_rhythm_period.assert_called_once_with(
            rhythm=rhythm, reference_date=first_of_month, cache=cache
        )
        mock_get_last_day_of_rhythm_period.assert_called_once_with(
            rhythm=rhythm, reference_date=first_of_month, cache=cache
        )
        mock_get_or_create_mandate_ref.assert_called_once_with(
            member=member, cache=cache
        )
        mock_get_already_paid_amount.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            product_type_name="pt_test_name",
        )
        mock_get_total_to_pay.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            subscriptions=subscriptions,
            cache=cache,
        )
        mock_get_payment_due_date_on_month.assert_not_called()
