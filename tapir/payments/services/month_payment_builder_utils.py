import datetime
from decimal import Decimal

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_first_of_next_month
from tapir.wirgarten.models import (
    Payment,
    MandateReference,
    Member,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import get_or_create_mandate_ref


class MonthPaymentBuilderUtils:
    @classmethod
    def get_payment_range_start(
        cls,
        first_day_of_rhythm_period: datetime.date,
        last_day_of_rhythm_period: datetime.date,
        mandate_ref: MandateReference,
        payment_type: str,
        generated_payments: set[Payment],
        cache: dict,
    ):
        relevant_past_payments = cls.get_relevant_past_payments(
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            mandate_ref=mandate_ref,
            payment_type=payment_type,
            generated_payments=generated_payments,
            cache=cache,
        )
        if len(relevant_past_payments) == 0:
            return first_day_of_rhythm_period

        return max(
            payment.subscription_payment_range_end for payment in relevant_past_payments
        ) + datetime.timedelta(days=1)

    @classmethod
    def get_relevant_past_payments(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        mandate_ref: MandateReference,
        payment_type: str,
        cache: dict,
        generated_payments: set[Payment],
    ):
        existing_payments = TapirCache.get_payments_by_mandate_ref_and_type(
            cache=cache, mandate_ref=mandate_ref, payment_type=payment_type
        )

        existing_payments = existing_payments.union(
            payment
            for payment in generated_payments
            if payment.mandate_ref_id == mandate_ref.ref
            and payment.type == payment_type
        )

        payments_for_this_period = [
            payment
            for payment in existing_payments
            if DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=range_start,
                range_1_end=range_end,
                range_2_start=payment.subscription_payment_range_start,
                range_2_end=payment.subscription_payment_range_end,
            )
        ]

        return payments_for_this_period

    @classmethod
    def get_already_paid_amount(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        mandate_ref: MandateReference,
        payment_type: str,
        cache: dict,
        generated_payments: set[Payment],
    ) -> Decimal:
        relevant_payments = cls.get_relevant_past_payments(
            range_start=range_start,
            range_end=range_end,
            mandate_ref=mandate_ref,
            payment_type=payment_type,
            cache=cache,
            generated_payments=generated_payments,
        )

        return sum([payment.amount for payment in relevant_payments], start=Decimal(0))

    @classmethod
    def get_payment_due_date_on_month(cls, reference_date: datetime.date, cache: dict):
        return reference_date.replace(
            day=get_parameter_value(ParameterKeys.PAYMENT_DUE_DAY, cache=cache)
        )

    @classmethod
    def build_payment_for_contract_and_member(
        cls,
        member: Member,
        contracts: set[Subscription | SolidarityContribution],
        first_of_month: datetime.date,
        rhythm,
        cache: dict,
        generated_payments: set[Payment],
        in_trial: bool,
        total_to_pay_function,
        payment_type: str,
        allow_negative_amounts: bool,
    ) -> Payment | None:
        first_day_of_rhythm_period = (
            MemberPaymentRhythmService.get_first_day_of_rhythm_period(
                rhythm=rhythm, reference_date=first_of_month, cache=cache
            )
        )
        last_day_of_rhythm_period = (
            MemberPaymentRhythmService.get_last_day_of_rhythm_period(
                rhythm=rhythm, reference_date=first_of_month, cache=cache
            )
        )

        payment_start_date = get_parameter_value(
            key=ParameterKeys.PAYMENT_START_DATE, cache=cache
        )
        first_day_of_rhythm_period = max(payment_start_date, first_day_of_rhythm_period)
        if first_day_of_rhythm_period > last_day_of_rhythm_period:
            return None

        mandate_ref = get_or_create_mandate_ref(member=member, cache=cache)

        already_paid = MonthPaymentBuilderUtils.get_already_paid_amount(
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            mandate_ref=mandate_ref,
            payment_type=payment_type,
            cache=cache,
            generated_payments=generated_payments,
        )
        total_to_pay = total_to_pay_function(
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            contracts=contracts,
            cache=cache,
        )

        new_payment_amount = total_to_pay - already_paid
        new_payment_amount = Decimal(new_payment_amount).quantize(Decimal("0.01"))
        if (
            new_payment_amount == 0
            or new_payment_amount < 0
            and not allow_negative_amounts
        ):
            return None

        payments_due_date = MonthPaymentBuilderUtils.get_payment_due_date_on_month(
            reference_date=(
                get_first_of_next_month(first_of_month) if in_trial else first_of_month
            ),
            cache=cache,
        )

        subscription_payment_range_start = (
            MonthPaymentBuilderUtils.get_payment_range_start(
                cache=cache,
                first_day_of_rhythm_period=first_day_of_rhythm_period,
                generated_payments=generated_payments,
                last_day_of_rhythm_period=last_day_of_rhythm_period,
                mandate_ref=mandate_ref,
                payment_type=payment_type,
            )
        )

        return Payment(
            due_date=payments_due_date,
            amount=new_payment_amount,
            mandate_ref=mandate_ref,
            status=Payment.PaymentStatus.DUE,
            type=payment_type,
            subscription_payment_range_start=subscription_payment_range_start,
            subscription_payment_range_end=last_day_of_rhythm_period,
        )
