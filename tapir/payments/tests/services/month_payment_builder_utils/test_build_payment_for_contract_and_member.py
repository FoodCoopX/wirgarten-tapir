import datetime
from decimal import Decimal
from unittest.mock import patch, Mock, call

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    MandateReferenceFactory,
    ProductTypeFactory,
)


class TestBuildPaymentForContractAndMember(TapirUnitTest):
    @patch.object(TrialPeriodManager, "get_trial_period_start_date", autospec=True)
    @patch.object(
        MonthPaymentBuilderUtils, "get_payment_due_date_on_month", autospec=True
    )
    @patch.object(MonthPaymentBuilderSubscriptions, "get_total_to_pay", autospec=True)
    @patch.object(MonthPaymentBuilderUtils, "get_already_paid_amount", autospec=True)
    @patch(
        "tapir.payments.services.month_payment_builder_utils.get_or_create_mandate_ref",
        autospec=True,
    )
    @patch.object(
        MemberPaymentRhythmService, "get_last_day_of_rhythm_period", autospec=True
    )
    @patch.object(
        MemberPaymentRhythmService, "get_first_day_of_rhythm_period", autospec=True
    )
    def test_buildPaymentForContractAndMember_totalToPayIsMoreThanAlreadyPaid_returnsPaymentWithDifference(
        self,
        mock_get_first_day_of_rhythm_period: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
        mock_get_or_create_mandate_ref: Mock,
        mock_get_already_paid_amount: Mock,
        mock_get_total_to_pay: Mock,
        mock_get_payment_due_date_on_month: Mock,
        mock_get_trial_period_start_date: Mock,
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
        mock_get_trial_period_start_date.return_value = datetime.date(
            year=2026, month=1, day=1
        )

        cache = {}
        mock_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_ENABLED, value=True, cache=cache
        )
        mock_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_DURATION, value=4, cache=cache
        )
        mock_parameter_value(
            key=ParameterKeys.PAYMENT_START_DATE,
            value=datetime.date(year=2026, month=6, day=1),
            cache=cache,
        )

        first_of_month = Mock()
        product_type = ProductTypeFactory.build(name="pt_test_name")
        subscriptions = SubscriptionFactory.build_batch(
            size=3,
            product__type=product_type,
            member=member,
            mandate_ref=mandate_ref,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        rhythm = Mock()

        generated_payments = Mock()

        payment = MonthPaymentBuilderUtils.build_payment_for_contract_and_member(
            member=member,
            first_of_month=first_of_month,
            contracts=set(subscriptions),
            payment_type=product_type.name,
            rhythm=rhythm,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=False,
            total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
            allow_negative_amounts=False,
        )

        self.assertIsNotNone(
            payment, "Payment should have been built since there is 7.5 left to pay"
        )
        self.assertEqual(due_date, payment.due_date)
        self.assertEqual(Decimal(7.5), payment.amount)
        self.assertEqual(mandate_ref, payment.mandate_ref)
        self.assertEqual(Payment.PaymentStatus.DUE, payment.status)
        self.assertEqual("pt_test_name", payment.type)
        self.assertEqual(
            datetime.date(year=2026, month=7, day=1),
            payment.subscription_payment_range_start,
        )
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
            payment_type="pt_test_name",
            cache=cache,
            generated_payments=generated_payments,
        )
        mock_get_total_to_pay.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            contracts=set(subscriptions),
            cache=cache,
        )
        mock_get_payment_due_date_on_month.assert_called_once_with(
            reference_date=first_of_month, cache=cache
        )
        self.assertEqual(3, mock_get_trial_period_start_date.call_count)
        mock_get_trial_period_start_date.assert_has_calls(
            [
                call(contract=subscription, cache=cache)
                for subscription in subscriptions
            ],
            any_order=True,
        )

    @patch("tapir.payments.services.month_payment_builder_utils.get_parameter_value")
    @patch.object(MonthPaymentBuilderUtils, "get_payment_due_date_on_month")
    @patch.object(MonthPaymentBuilderSubscriptions, "get_total_to_pay")
    @patch.object(MonthPaymentBuilderUtils, "get_already_paid_amount")
    @patch(
        "tapir.payments.services.month_payment_builder_utils.get_or_create_mandate_ref"
    )
    @patch.object(MemberPaymentRhythmService, "get_last_day_of_rhythm_period")
    @patch.object(MemberPaymentRhythmService, "get_first_day_of_rhythm_period")
    def test_buildPaymentForContractAndMember_totalToPayIsEqualToAlreadyPaid_returnsNone(
        self,
        mock_get_first_day_of_rhythm_period: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
        mock_get_or_create_mandate_ref: Mock,
        mock_get_already_paid_amount: Mock,
        mock_get_total_to_pay: Mock,
        mock_get_payment_due_date_on_month: Mock,
        mock_get_parameter_value: Mock,
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
        mock_get_parameter_value.return_value = datetime.date(year=2026, month=6, day=1)

        first_of_month = Mock()
        product_type = ProductTypeFactory.build(name="pt_test_name")
        subscriptions = SubscriptionFactory.build_batch(
            size=3, product__type=product_type, member=member, mandate_ref=mandate_ref
        )
        rhythm = Mock()
        cache = Mock()
        generated_payments = Mock()

        payment = MonthPaymentBuilderUtils.build_payment_for_contract_and_member(
            member=member,
            first_of_month=first_of_month,
            contracts=set(subscriptions),
            payment_type=product_type.name,
            rhythm=rhythm,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=False,
            total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
            allow_negative_amounts=False,
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
            payment_type="pt_test_name",
            cache=cache,
            generated_payments=generated_payments,
        )
        mock_get_total_to_pay.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            contracts=set(subscriptions),
            cache=cache,
        )
        mock_get_payment_due_date_on_month.assert_not_called()
        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.PAYMENT_START_DATE, cache=cache
        )

    @patch("tapir.payments.services.month_payment_builder_utils.get_parameter_value")
    @patch.object(MonthPaymentBuilderUtils, "get_payment_due_date_on_month")
    @patch.object(MonthPaymentBuilderSubscriptions, "get_total_to_pay")
    @patch.object(MonthPaymentBuilderUtils, "get_already_paid_amount")
    @patch(
        "tapir.payments.services.month_payment_builder_utils.get_or_create_mandate_ref"
    )
    @patch.object(MemberPaymentRhythmService, "get_last_day_of_rhythm_period")
    @patch.object(MemberPaymentRhythmService, "get_first_day_of_rhythm_period")
    def test_buildPaymentForContractAndMember_totalToPayIsLessThanAlreadyPaid_returnsNone(
        self,
        mock_get_first_day_of_rhythm_period: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
        mock_get_or_create_mandate_ref: Mock,
        mock_get_already_paid_amount: Mock,
        mock_get_total_to_pay: Mock,
        mock_get_payment_due_date_on_month: Mock,
        mock_get_parameter_value: Mock,
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
        mock_get_parameter_value.return_value = datetime.date(year=2026, month=6, day=1)

        first_of_month = Mock()
        product_type = ProductTypeFactory.build(name="pt_test_name")
        subscriptions = SubscriptionFactory.build_batch(
            size=3, product__type=product_type, member=member, mandate_ref=mandate_ref
        )
        rhythm = Mock()
        cache = Mock()
        generated_payments = Mock()

        payment = MonthPaymentBuilderUtils.build_payment_for_contract_and_member(
            member=member,
            first_of_month=first_of_month,
            contracts=set(subscriptions),
            payment_type=product_type.name,
            rhythm=rhythm,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=False,
            total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
            allow_negative_amounts=False,
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
            payment_type="pt_test_name",
            cache=cache,
            generated_payments=generated_payments,
        )
        mock_get_total_to_pay.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            contracts=set(subscriptions),
            cache=cache,
        )
        mock_get_payment_due_date_on_month.assert_not_called()
        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.PAYMENT_START_DATE, cache=cache
        )

    @patch.object(TrialPeriodManager, "get_trial_period_start_date", autospec=True)
    @patch.object(MonthPaymentBuilderUtils, "get_payment_due_date_on_month")
    @patch.object(MonthPaymentBuilderSubscriptions, "get_total_to_pay")
    @patch.object(MonthPaymentBuilderUtils, "get_already_paid_amount")
    @patch(
        "tapir.payments.services.month_payment_builder_utils.get_or_create_mandate_ref"
    )
    @patch.object(MemberPaymentRhythmService, "get_last_day_of_rhythm_period")
    @patch.object(MemberPaymentRhythmService, "get_first_day_of_rhythm_period")
    def test_buildPaymentForContractAndMember_totalToPayIsLessThanAlreadyPaidButNegativePaymentAllowed_returnsPaymentWithNegativeValue(
        self,
        mock_get_first_day_of_rhythm_period: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
        mock_get_or_create_mandate_ref: Mock,
        mock_get_already_paid_amount: Mock,
        mock_get_total_to_pay: Mock,
        mock_get_payment_due_date_on_month: Mock,
        mock_get_trial_period_start_date: Mock,
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
        due_date = datetime.date(year=2026, month=7, day=13)
        mock_get_payment_due_date_on_month.return_value = due_date
        mock_get_trial_period_start_date.return_value = datetime.date(
            year=2026, month=1, day=1
        )

        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.PAYMENT_START_DATE,
            value=datetime.date(year=2026, month=6, day=1),
        )
        mock_parameter_value(
            cache=cache, key=ParameterKeys.TRIAL_PERIOD_ENABLED, value=True
        )
        mock_parameter_value(
            cache=cache, key=ParameterKeys.TRIAL_PERIOD_DURATION, value=4
        )

        first_of_month = Mock()
        product_type = ProductTypeFactory.build(name="pt_test_name")
        subscriptions = SubscriptionFactory.build_batch(
            size=3,
            product__type=product_type,
            member=member,
            mandate_ref=mandate_ref,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        rhythm = Mock()
        generated_payments = Mock()

        payment = MonthPaymentBuilderUtils.build_payment_for_contract_and_member(
            member=member,
            first_of_month=first_of_month,
            contracts=set(subscriptions),
            payment_type=product_type.name,
            rhythm=rhythm,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=False,
            total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
            allow_negative_amounts=True,
        )

        self.assertIsNotNone(payment)
        self.assertEqual(due_date, payment.due_date)
        self.assertEqual(Decimal(-2.5), payment.amount)
        self.assertEqual(mandate_ref, payment.mandate_ref)
        self.assertEqual(Payment.PaymentStatus.DUE, payment.status)
        self.assertEqual("pt_test_name", payment.type)
        self.assertEqual(
            datetime.date(year=2026, month=7, day=1),
            payment.subscription_payment_range_start,
        )
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
            payment_type="pt_test_name",
            cache=cache,
            generated_payments=generated_payments,
        )
        mock_get_total_to_pay.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            contracts=set(subscriptions),
            cache=cache,
        )
        mock_get_payment_due_date_on_month.assert_called_once_with(
            reference_date=first_of_month, cache=cache
        )
        self.assertEqual(3, mock_get_trial_period_start_date.call_count)
        mock_get_trial_period_start_date.assert_has_calls(
            [
                call(contract=subscription, cache=cache)
                for subscription in subscriptions
            ],
            any_order=True,
        )

    @patch.object(TrialPeriodManager, "get_trial_period_start_date", autospec=True)
    @patch.object(MonthPaymentBuilderUtils, "get_payment_due_date_on_month")
    @patch.object(MonthPaymentBuilderSubscriptions, "get_total_to_pay")
    @patch.object(MonthPaymentBuilderUtils, "get_already_paid_amount")
    @patch(
        "tapir.payments.services.month_payment_builder_utils.get_or_create_mandate_ref"
    )
    @patch.object(MemberPaymentRhythmService, "get_last_day_of_rhythm_period")
    @patch.object(MemberPaymentRhythmService, "get_first_day_of_rhythm_period")
    def test_buildPaymentForContractAndMember_subscriptionIsInTrial_returnsPaymentWithDueDateNextMonth(
        self,
        mock_get_first_day_of_rhythm_period: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
        mock_get_or_create_mandate_ref: Mock,
        mock_get_already_paid_amount: Mock,
        mock_get_total_to_pay: Mock,
        mock_get_payment_due_date_on_month: Mock,
        mock_get_trial_period_start_date: Mock,
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
        mock_get_trial_period_start_date.return_value = datetime.date(
            year=2026, month=7, day=1
        )

        cache = {}
        mock_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_ENABLED, value=True, cache=cache
        )
        mock_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_DURATION, value=4, cache=cache
        )
        mock_parameter_value(
            key=ParameterKeys.PAYMENT_START_DATE,
            value=datetime.date(year=2026, month=6, day=1),
            cache=cache,
        )

        first_of_month = datetime.date(year=2026, month=6, day=10)
        product_type = ProductTypeFactory.build(name="pt_test_name")
        subscriptions = SubscriptionFactory.build_batch(
            size=3,
            product__type=product_type,
            member=member,
            mandate_ref=mandate_ref,
            start_date=datetime.date(year=2026, month=7, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        rhythm = Mock()
        generated_payments = Mock()

        payment = MonthPaymentBuilderUtils.build_payment_for_contract_and_member(
            member=member,
            first_of_month=first_of_month,
            contracts=set(subscriptions),
            payment_type=product_type.name,
            rhythm=rhythm,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=True,
            total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
            allow_negative_amounts=False,
        )

        self.assertIsNotNone(
            payment, "Payment should have been built since there is 7.5 left to pay"
        )
        self.assertEqual(due_date, payment.due_date)
        self.assertEqual(Decimal(7.5), payment.amount)
        self.assertEqual(mandate_ref, payment.mandate_ref)
        self.assertEqual(Payment.PaymentStatus.DUE, payment.status)
        self.assertEqual("pt_test_name", payment.type)
        self.assertEqual(
            datetime.date(year=2026, month=7, day=1),
            payment.subscription_payment_range_start,
        )
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
            payment_type="pt_test_name",
            cache=cache,
            generated_payments=generated_payments,
        )
        mock_get_total_to_pay.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            contracts=set(subscriptions),
            cache=cache,
        )
        mock_get_payment_due_date_on_month.assert_called_once_with(
            reference_date=datetime.date(year=2026, month=7, day=1), cache=cache
        )
        self.assertEqual(3, mock_get_trial_period_start_date.call_count)
        mock_get_trial_period_start_date.assert_has_calls(
            [
                call(contract=subscription, cache=cache)
                for subscription in subscriptions
            ],
            any_order=True,
        )

    @patch("tapir.payments.services.month_payment_builder_utils.get_parameter_value")
    @patch.object(MonthPaymentBuilderUtils, "get_payment_due_date_on_month")
    @patch.object(MonthPaymentBuilderSubscriptions, "get_total_to_pay")
    @patch.object(MonthPaymentBuilderUtils, "get_already_paid_amount")
    @patch(
        "tapir.payments.services.month_payment_builder_utils.get_or_create_mandate_ref"
    )
    @patch.object(MemberPaymentRhythmService, "get_last_day_of_rhythm_period")
    @patch.object(MemberPaymentRhythmService, "get_first_day_of_rhythm_period")
    def test_buildPaymentForContractAndMember_rangeEndIsBeforePaymentsStart_returnsNone(
        self,
        mock_get_first_day_of_rhythm_period: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
        mock_get_or_create_mandate_ref: Mock,
        mock_get_already_paid_amount: Mock,
        mock_get_total_to_pay: Mock,
        mock_get_payment_due_date_on_month: Mock,
        mock_get_parameter_value: Mock,
    ):
        range_start = datetime.date(year=2026, month=7, day=1)
        mock_get_first_day_of_rhythm_period.return_value = range_start
        range_end = datetime.date(year=2026, month=7, day=31)
        mock_get_last_day_of_rhythm_period.return_value = range_end
        member = MemberFactory.build()
        mock_get_parameter_value.return_value = datetime.date(year=2026, month=8, day=1)

        first_of_month = Mock()
        rhythm = Mock()
        cache = Mock()
        generated_payments = Mock()

        payment = MonthPaymentBuilderUtils.build_payment_for_contract_and_member(
            member=member,
            first_of_month=first_of_month,
            contracts=Mock(),
            payment_type=Mock(),
            rhythm=rhythm,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=False,
            total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
            allow_negative_amounts=False,
        )

        self.assertIsNone(
            payment,
            "Payment should not have been built because the payment start date from the config is after the end of the interval",
        )

        mock_get_first_day_of_rhythm_period.assert_called_once_with(
            rhythm=rhythm, reference_date=first_of_month, cache=cache
        )
        mock_get_last_day_of_rhythm_period.assert_called_once_with(
            rhythm=rhythm, reference_date=first_of_month, cache=cache
        )
        mock_get_or_create_mandate_ref.assert_not_called()
        mock_get_already_paid_amount.assert_not_called()
        mock_get_total_to_pay.assert_not_called()
        mock_get_payment_due_date_on_month.assert_not_called()
        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.PAYMENT_START_DATE, cache=cache
        )

    @patch.object(TrialPeriodManager, "get_trial_period_start_date", autospec=True)
    @patch.object(MonthPaymentBuilderUtils, "get_payment_due_date_on_month")
    @patch.object(MonthPaymentBuilderSubscriptions, "get_total_to_pay")
    @patch.object(MonthPaymentBuilderUtils, "get_already_paid_amount")
    @patch(
        "tapir.payments.services.month_payment_builder_utils.get_or_create_mandate_ref"
    )
    @patch.object(MemberPaymentRhythmService, "get_last_day_of_rhythm_period")
    @patch.object(MemberPaymentRhythmService, "get_first_day_of_rhythm_period")
    def test_buildPaymentForContractAndMember_paymentStartIsInsideTheRange_returnsPartialPayment(
        self,
        mock_get_first_day_of_rhythm_period: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
        mock_get_or_create_mandate_ref: Mock,
        mock_get_already_paid_amount: Mock,
        mock_get_total_to_pay: Mock,
        mock_get_payment_due_date_on_month: Mock,
        mock_get_trial_period_start_date: Mock,
    ):
        range_start = datetime.date(year=2026, month=6, day=1)
        mock_get_first_day_of_rhythm_period.return_value = range_start
        range_end = datetime.date(year=2026, month=7, day=31)
        mock_get_last_day_of_rhythm_period.return_value = range_end
        member = MemberFactory.build()
        mandate_ref = MandateReferenceFactory.build(member=member, ref="test_ref")
        mock_get_or_create_mandate_ref.return_value = mandate_ref
        mock_get_already_paid_amount.return_value = 0
        mock_get_total_to_pay.return_value = 17.5
        due_date = datetime.date(year=2026, month=6, day=5)
        mock_get_payment_due_date_on_month.return_value = due_date
        payment_start_date = datetime.date(year=2026, month=7, day=12)
        mock_get_trial_period_start_date.return_value = datetime.date(
            year=2026, month=1, day=1
        )

        cache = {}
        mock_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_ENABLED, value=True, cache=cache
        )
        mock_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_DURATION, value=4, cache=cache
        )
        mock_parameter_value(
            key=ParameterKeys.PAYMENT_START_DATE,
            value=payment_start_date,
            cache=cache,
        )

        first_of_month = Mock()
        product_type = ProductTypeFactory.build(name="pt_test_name")
        subscriptions = SubscriptionFactory.build_batch(
            size=3,
            product__type=product_type,
            member=member,
            mandate_ref=mandate_ref,
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        rhythm = Mock()
        generated_payments = Mock()

        payment = MonthPaymentBuilderUtils.build_payment_for_contract_and_member(
            member=member,
            first_of_month=first_of_month,
            contracts=set(subscriptions),
            payment_type=product_type.name,
            rhythm=rhythm,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=False,
            total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
            allow_negative_amounts=False,
        )

        self.assertIsNotNone(
            payment,
            "There should be a payment since the range end is after the payment start date from the config",
        )
        self.assertEqual(due_date, payment.due_date)
        self.assertEqual(Decimal(17.5), payment.amount)
        self.assertEqual(mandate_ref, payment.mandate_ref)
        self.assertEqual(Payment.PaymentStatus.DUE, payment.status)
        self.assertEqual("pt_test_name", payment.type)
        self.assertEqual(
            datetime.date(year=2026, month=7, day=12),
            payment.subscription_payment_range_start,
        )
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
            range_start=payment_start_date,
            range_end=range_end,
            mandate_ref=mandate_ref,
            payment_type="pt_test_name",
            cache=cache,
            generated_payments=generated_payments,
        )
        mock_get_total_to_pay.assert_called_once_with(
            range_start=payment_start_date,
            range_end=range_end,
            contracts=set(subscriptions),
            cache=cache,
        )
        mock_get_payment_due_date_on_month.assert_called_once_with(
            reference_date=first_of_month, cache=cache
        )
        self.assertEqual(3, mock_get_trial_period_start_date.call_count)
        mock_get_trial_period_start_date.assert_has_calls(
            [
                call(contract=subscription, cache=cache)
                for subscription in subscriptions
            ],
            any_order=True,
        )

    @patch.object(MonthPaymentBuilderSubscriptions, "get_total_to_pay")
    @patch.object(MonthPaymentBuilderUtils, "get_already_paid_amount")
    @patch(
        "tapir.payments.services.month_payment_builder_utils.get_or_create_mandate_ref"
    )
    @patch.object(MemberPaymentRhythmService, "get_last_day_of_rhythm_period")
    @patch.object(MemberPaymentRhythmService, "get_first_day_of_rhythm_period")
    def test_buildPaymentForContractAndMember_contractWithoutTrialStartedAfterDueDateThisMonth_returnsPaymentWithDueDateNextMonth(
        self,
        mock_get_first_day_of_rhythm_period: Mock,
        mock_get_last_day_of_rhythm_period: Mock,
        mock_get_or_create_mandate_ref: Mock,
        mock_get_already_paid_amount: Mock,
        mock_get_total_to_pay: Mock,
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

        cache = {}
        mock_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_ENABLED, value=False, cache=cache
        )
        mock_parameter_value(
            key=ParameterKeys.PAYMENT_START_DATE,
            value=datetime.date(year=2026, month=6, day=1),
            cache=cache,
        )
        mock_parameter_value(
            key=ParameterKeys.PAYMENT_DUE_DAY,
            value=10,
            cache=cache,
        )

        first_of_month = datetime.date(year=2026, month=7, day=1)
        product_type = ProductTypeFactory.build(name="pt_test_name")
        subscriptions = SubscriptionFactory.build_batch(
            size=3,
            product__type=product_type,
            member=member,
            mandate_ref=mandate_ref,
            start_date=datetime.date(year=2026, month=7, day=15),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        rhythm = Mock()
        generated_payments = Mock()

        payment = MonthPaymentBuilderUtils.build_payment_for_contract_and_member(
            member=member,
            first_of_month=first_of_month,
            contracts=set(subscriptions),
            payment_type=product_type.name,
            rhythm=rhythm,
            cache=cache,
            generated_payments=generated_payments,
            in_trial=False,
            total_to_pay_function=MonthPaymentBuilderSubscriptions.get_total_to_pay,
            allow_negative_amounts=False,
        )

        self.assertIsNotNone(
            payment, "Payment should have been built since there is 7.5 left to pay"
        )
        self.assertEqual(
            datetime.date(year=2026, month=8, day=10),
            payment.due_date,
            "The subscription starts on the 15th, the payment day is the 10th, the we can't create a payment on the 10/07. It gets created on the 10/08 instead",
        )
        self.assertEqual(Decimal(7.5), payment.amount)
        self.assertEqual(mandate_ref, payment.mandate_ref)
        self.assertEqual(Payment.PaymentStatus.DUE, payment.status)
        self.assertEqual("pt_test_name", payment.type)
        self.assertEqual(
            datetime.date(year=2026, month=7, day=15),
            payment.subscription_payment_range_start,
        )
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
            payment_type="pt_test_name",
            cache=cache,
            generated_payments=generated_payments,
        )
        mock_get_total_to_pay.assert_called_once_with(
            range_start=range_start,
            range_end=range_end,
            contracts=set(subscriptions),
            cache=cache,
        )
