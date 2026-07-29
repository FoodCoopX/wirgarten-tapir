import datetime
from decimal import Decimal

from tapir.associations.models import AssociationMembership
from tapir.configuration.parameter import get_parameter_value
from tapir.payments.models import MemberCredit
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.types import TapirContract
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_first_of_next_month, get_last_day_of_month
from tapir.wirgarten.models import (
    Payment,
    MandateReference,
    Member,
)
from tapir.wirgarten.parameter_keys import ParameterKeys


class MonthPaymentBuilderUtils:
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
    def get_relevant_credits(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        member_id: str,
        payment_type: str,
        cache: dict,
        generated_credits: set[MemberCredit],
    ) -> list[MemberCredit]:
        member_credits = list(
            TapirCache.get_member_credits(cache=cache, member_id=member_id)
        )
        member_credits.extend(
            credit for credit in generated_credits if credit.member_id == member_id
        )
        return [
            credit
            for credit in member_credits
            if credit.source == payment_type
            and range_start <= credit.due_date <= range_end
        ]

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
        sum_paid = sum(
            [payment.amount for payment in relevant_payments], start=Decimal(0)
        )

        relevant_credits = cls.get_relevant_credits(
            range_start=range_start,
            range_end=range_end,
            member_id=mandate_ref.member_id,
            payment_type=payment_type,
            cache=cache,
            generated_credits=set(),
        )
        sum_credits = sum(
            [credit.amount for credit in relevant_credits], start=Decimal(0)
        )

        return sum_paid - sum_credits

    @classmethod
    def get_payment_due_date_on_month(cls, reference_date: datetime.date, cache: dict):
        return reference_date.replace(
            day=get_parameter_value(ParameterKeys.PAYMENT_DUE_DAY, cache=cache)
        )

    @classmethod
    def build_payment_for_contract_and_member(
        cls,
        member: Member,
        contracts: set[TapirContract],
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

        mandate_ref = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache=cache
        )

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

        payments_due_date = cls.get_payment_due_date(
            first_of_month, in_trial, contracts, cache
        )

        subscription_payment_range_start, subscription_payment_range_end = (
            cls.get_payment_range(
                contracts=contracts,
                first_day_of_rhythm_period=first_day_of_rhythm_period,
                last_day_of_rhythm_period=last_day_of_rhythm_period,
                in_trial=in_trial,
                cache=cache,
            )
        )

        return Payment(
            due_date=payments_due_date,
            amount=new_payment_amount,
            mandate_ref=mandate_ref,
            status=Payment.PaymentStatus.DUE,
            type=payment_type,
            subscription_payment_range_start=subscription_payment_range_start,
            subscription_payment_range_end=subscription_payment_range_end,
        )

    @classmethod
    def get_payment_due_date(
        cls,
        first_of_month: datetime.date,
        in_trial: bool,
        contracts: set[TapirContract],
        cache: dict,
    ) -> datetime.date:
        payments_due_date = cls.get_payment_due_date_on_month(
            reference_date=(
                get_first_of_next_month(first_of_month) if in_trial else first_of_month
            ),
            cache=cache,
        )

        minimum_due_date = min(
            cls.get_minimum_due_date(contract=contract, cache=cache)
            for contract in contracts
        )
        if minimum_due_date > payments_due_date:
            payments_due_date = cls.get_payment_due_date_on_month(
                reference_date=(get_first_of_next_month(payments_due_date)),
                cache=cache,
            )
        return payments_due_date

    @classmethod
    def get_minimum_due_date(cls, contract: TapirContract, cache: dict):
        if isinstance(contract, AssociationMembership) and get_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
        ):
            first_of_this_month = contract.start_date.replace(day=1)
            subscriptions = TapirCache.get_active_and_future_subscriptions_by_member_id(
                reference_date=first_of_this_month, cache=cache
            ).get(contract.member_id, [])
            if all(
                TrialPeriodManager.is_contract_in_trial(
                    contract=subscription,
                    reference_date=first_of_this_month,
                    cache=cache,
                )
                for subscription in subscriptions
            ):
                return get_first_of_next_month(contract.start_date)

        if contract.created_at:
            # Renewed contracts that are planned but not saved yet don't have a created_at yet.
            return contract.created_at.date()
        return contract.start_date

    @classmethod
    def get_payment_range(
        cls,
        contracts: set[TapirContract],
        first_day_of_rhythm_period: datetime.date,
        last_day_of_rhythm_period: datetime.date,
        in_trial: bool,
        cache: dict,
    ) -> tuple[datetime.date, datetime.date]:
        if in_trial:
            return cls.get_payment_range_for_contracts_in_trial(
                last_day_of_rhythm_period,
                contracts,
                first_day_of_rhythm_period,
                cache,
            )

        return cls.get_payment_range_for_contracts_not_in_trial(
            last_day_of_rhythm_period,
            contracts,
            first_day_of_rhythm_period,
            cache,
        )

    @classmethod
    def get_payment_range_for_contracts_not_in_trial(
        cls,
        last_day_of_rhythm_period: datetime.date,
        contracts: set[TapirContract],
        first_day_of_rhythm_period: datetime.date,
        cache: dict,
    ) -> tuple[datetime.date, datetime.date]:
        trial_period_ends = [
            TrialPeriodManager.get_last_day_of_trial_period(contract, cache=cache)
            for contract in contracts
            if not isinstance(contract, AssociationMembership)
        ]
        trial_period_ends = [date for date in trial_period_ends if date is not None]
        if len(trial_period_ends) == 0:
            subscription_payment_range_start = max(
                first_day_of_rhythm_period,
                min(contract.start_date for contract in contracts),
            )
        else:
            trial_period_end = min(trial_period_ends)
            trial_period_end_for_payment = get_last_day_of_month(trial_period_end)
            subscription_payment_range_start = max(
                first_day_of_rhythm_period,
                trial_period_end_for_payment + datetime.timedelta(days=1),
                min(contract.start_date for contract in contracts),
            )

        if any(contract.end_date is None for contract in contracts):
            subscription_payment_range_end = last_day_of_rhythm_period
        else:
            subscription_payment_range_end = min(
                last_day_of_rhythm_period,
                max(contract.end_date for contract in contracts),
            )
        return subscription_payment_range_start, subscription_payment_range_end

    @classmethod
    def get_payment_range_for_contracts_in_trial(
        cls,
        last_day_of_rhythm_period: datetime.date,
        contracts: set[TapirContract],
        first_day_of_rhythm_period: datetime.date,
        cache: dict,
    ) -> tuple[datetime.date, datetime.date]:
        subscription_payment_range_start = max(
            first_day_of_rhythm_period,
            min(contract.start_date for contract in contracts),
        )
        subscription_payment_range_end = min(
            last_day_of_rhythm_period,
            max(
                TrialPeriodManager.get_last_day_of_trial_period(contract, cache=cache)
                for contract in contracts
            ),
            max(contract.end_date for contract in contracts),
        )
        subscription_payment_range_end = get_last_day_of_month(
            subscription_payment_range_end
        )
        return subscription_payment_range_start, subscription_payment_range_end
