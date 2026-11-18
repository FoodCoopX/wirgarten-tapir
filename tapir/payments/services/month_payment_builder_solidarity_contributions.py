import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.utils.formats import date_format

from tapir.utils.dataclasses import CalculationPart
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
from tapir.utils.shortcuts import get_last_day_of_month
from tapir.wirgarten.models import (
    Payment,
    Member,
)
from tapir.wirgarten.utils import format_currency


class MonthPaymentBuilderSolidarityContributions:
    PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION = "payment_type_solidarity_contribution"

    @classmethod
    def build_payments_for_solidarity_contributions(
        cls,
        current_month: datetime.date,
        cache: dict,
        generated_payments: set[Payment],
        in_trial: bool,
        member_id: str | None = None,
    ) -> list[Payment]:
        target_month = current_month
        if in_trial:
            target_month = (target_month - relativedelta(months=1)).replace(day=1)

        solidarity_contributions = MonthPaymentBuilderUtils.filter_contracts_by_member(
            contracts=cls.get_solidarity_contributions_for_this_and_the_next_growing_period(
                cache=cache, first_of_month=target_month, is_in_trial=in_trial
            ),
            member_id=member_id,
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
                calculation_parts_function=cls.get_calculation_parts,
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
        return sum(
            (
                part.value
                for part in cls.get_calculation_parts(
                    range_start=range_start,
                    range_end=range_end,
                    contracts=contracts,
                    cache=cache,
                )
            ),
            Decimal(0),
        )

    @classmethod
    def get_calculation_parts(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        contracts: list[SolidarityContribution],
        cache: dict,
    ) -> list[CalculationPart]:
        contributions_active_within_period = sorted(
            (
                contribution
                for contribution in contracts
                if DateRangeOverlapChecker.do_ranges_overlap(
                    range_1_start=range_start,
                    range_1_end=range_end,
                    range_2_start=contribution.start_date,
                    range_2_end=contribution.end_date,
                )
            ),
            key=lambda contribution: contribution.start_date,
        )
        return [
            part
            for contribution in contributions_active_within_period
            for part in cls._get_calculation_parts_for_single_contribution_within_range(
                contribution=contribution,
                range_start=range_start,
                range_end=range_end,
            )
        ]

    @classmethod
    def get_solidarity_contributions_for_this_and_the_next_growing_period(
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

        current_growing_period = TapirCache.get_growing_period_at_date(
            reference_date=first_of_month, cache=cache
        )
        if current_growing_period is None:
            return []

        next_growing_period = TapirCache.get_growing_period_at_date(
            reference_date=current_growing_period.end_date + datetime.timedelta(days=1),
            cache=cache,
        )
        range_start = current_growing_period.start_date
        range_end = (
            next_growing_period.end_date
            if next_growing_period
            else current_growing_period.end_date
        )

        return [
            contribution
            for contribution in existing_contributions.union(
                planned_renewed_contributions
            )
            if DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=contribution.start_date,
                range_1_end=contribution.end_date,
                range_2_start=range_start,
                range_2_end=range_end,
            )
            and TrialPeriodManager.is_contract_in_trial(
                contract=contribution, reference_date=first_of_month, cache=cache
            )
            == is_in_trial
        ]

    @classmethod
    def _get_calculation_parts_for_single_contribution_within_range(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        contribution: SolidarityContribution,
    ) -> list[CalculationPart]:
        parts = []
        current_month = range_start
        while current_month < range_end:
            part = cls._build_calculation_part_for_contribution_within_month(
                first_of_month=current_month, contribution=contribution
            )
            if part is not None:
                parts.append(part)
            current_month += relativedelta(months=1)

        return parts

    @classmethod
    def _build_calculation_part_for_contribution_within_month(
        cls, first_of_month: datetime.date, contribution: SolidarityContribution
    ) -> CalculationPart | None:
        nb_days_in_month = get_last_day_of_month(first_of_month).day
        nb_days_overlap = MonthPaymentBuilderUtils.get_number_of_days_covered_in_month(
            first_of_month=first_of_month,
            contract_start=contribution.start_date,
            contract_end=contribution.end_date,
        )
        if nb_days_overlap == 0:
            return None

        prefix = f"{date_format(first_of_month, "F Y")}, Solidarbeitrag"
        monthly_amount = format_currency(contribution.amount)
        if nb_days_overlap == nb_days_in_month:
            return CalculationPart(
                explanation=f"{prefix}: {monthly_amount} € monatlich (voller Monat)",
                value=contribution.amount,
            )

        ratio = nb_days_overlap / nb_days_in_month
        value = (contribution.amount * Decimal(ratio)).quantize(Decimal("0.01"))
        return CalculationPart(
            explanation=f"{prefix}: {monthly_amount} € × {nb_days_overlap} von {nb_days_in_month} Tagen = {format_currency(value)} €",
            value=value,
        )

    @classmethod
    def group_contributions_by_member(
        cls, contributions: list[SolidarityContribution]
    ) -> dict[Member, set[SolidarityContribution]]:
        contributions_by_member: dict[Member, set[SolidarityContribution]] = {}

        for contribution in contributions:
            if contribution.member not in contributions_by_member:
                contributions_by_member[contribution.member] = set()
            contributions_by_member[contribution.member].add(contribution)

        return contributions_by_member
