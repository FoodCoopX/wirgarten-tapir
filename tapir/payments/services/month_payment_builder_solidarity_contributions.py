import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.services.automatic_solidarity_contribution_renewal_service import (
    AutomaticSolidarityContributionRenewalService,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_last_day_of_month, get_first_of_next_month
from tapir.wirgarten.models import (
    Payment,
    Member,
)


class MonthPaymentBuilderSolidarityContributions:
    PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION = "payment_type_solidarity_contribution"

    @classmethod
    def build_payments_for_solidarity_contributions(
        cls,
        current_month: datetime.date,
        cache: dict,
        generated_payments: set[Payment],
        in_trial: bool,
    ) -> list[Payment]:
        target_month = current_month
        if in_trial:
            target_month = (target_month - relativedelta(months=1)).replace(day=1)

        solidarity_contributions = cls.get_current_and_renewed_solidarity_contributions(
            cache=cache, first_of_month=target_month, is_in_trial=in_trial
        )

        contributions_by_member = cls.group_contributions_by_member(
            solidarity_contributions
        )

        payments_to_create = []

        for (
            member,
            contributions,
        ) in contributions_by_member.items():
            rhythm = MemberPaymentRhythm.Rhythm.MONTHLY.value
            if not in_trial:
                rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
                    member=member, reference_date=target_month, cache=cache
                )

            payment = MonthPaymentBuilderUtils.build_payment_for_contract_and_member(
                member=member,
                first_of_month=target_month,
                contracts=contributions,
                rhythm=rhythm,
                cache=cache,
                generated_payments=generated_payments,
                in_trial=in_trial,
                payment_type=cls.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION,
                total_to_pay_function=cls.get_total_to_pay,
                allow_negative_amounts=True,
            )
            if payment is not None:
                payments_to_create.append(payment)

        return payments_to_create

    @classmethod
    def get_total_to_pay(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        contracts: list[SolidarityContribution],
        cache: dict,
    ) -> Decimal:
        contributions_active_within_period = [
            contribution
            for contribution in contracts
            if DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=range_start,
                range_1_end=range_end,
                range_2_start=contribution.start_date,
                range_2_end=contribution.end_date,
            )
        ]
        total_to_pay = sum(
            [
                cls.get_amount_for_single_contribution_within_range(
                    contribution=contribution,
                    range_start=range_start,
                    range_end=range_end,
                )
                for contribution in contributions_active_within_period
            ],
            Decimal(0),
        )
        return total_to_pay

    @classmethod
    def get_current_and_renewed_solidarity_contributions(
        cls, cache: dict, first_of_month: datetime.date, is_in_trial: bool
    ) -> list[SolidarityContribution]:
        existing_contributions = TapirCache.get_all_solidarity_contributions(
            cache=cache
        )

        planned_renewed_contributions = [
            AutomaticSolidarityContributionRenewalService.build_renewed_contribution(
                contribution=contribution, cache=cache
            )
            for contribution in AutomaticSolidarityContributionRenewalService.get_contributions_that_will_be_renewed(
                reference_date=first_of_month, cache=cache
            )
        ]

        return [
            contribution
            for contribution in existing_contributions.union(
                planned_renewed_contributions
            )
            if TrialPeriodManager.is_contract_in_trial(
                contract=contribution, reference_date=first_of_month, cache=cache
            )
            == is_in_trial
        ]

    @classmethod
    def get_amount_for_single_contribution_within_range(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        contribution: SolidarityContribution,
    ) -> Decimal:
        current_month = range_start
        total = Decimal(0)

        while current_month < range_end:
            total += cls.get_amount_to_pay_for_contribution_within_month(
                first_of_month=current_month, contribution=contribution
            )

            current_month += relativedelta(months=1)

        return total

    @classmethod
    def get_amount_to_pay_for_contribution_within_month(
        cls, first_of_month: datetime.date, contribution: SolidarityContribution
    ):
        nb_days_in_month = (
            get_first_of_next_month(first_of_month) - first_of_month
        ).days
        nb_days_overlap = DateRangeOverlapChecker.get_number_of_days_of_overlap(
            range_1_start=first_of_month,
            range_1_end=get_last_day_of_month(first_of_month),
            range_2_start=contribution.start_date,
            range_2_end=contribution.end_date,
        )
        ratio = nb_days_overlap / nb_days_in_month

        return (contribution.amount * Decimal(ratio)).quantize(Decimal("0.01"))

    @classmethod
    def group_contributions_by_member(
        cls, contributions: list[SolidarityContribution]
    ) -> dict[Member, set[SolidarityContribution]]:
        contributions_by_member: dict[Member, set[SolidarityContribution]] = {}

        for contribution in contributions:
            if contribution.member not in contributions_by_member.keys():
                contributions_by_member[contribution.member] = set()
            contributions_by_member[contribution.member].add(contribution)

        return contributions_by_member
