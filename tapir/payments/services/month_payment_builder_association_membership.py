import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.utils.formats import date_format

from tapir.associations.models import AssociationMembership
from tapir.associations.services.association_membership_price_type_getter import (
    AssociationMembershipTypePriceGetter,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.utils.dataclasses import CalculationPart
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_last_day_of_month
from tapir.wirgarten.models import (
    Payment,
    Member,
)
from tapir.wirgarten.utils import format_currency


class MonthPaymentBuilderAssociationMembership:
    PAYMENT_TYPE_ASSOCIATION_MEMBERSHIP = "payment_type_association_membership"

    @classmethod
    def build_payments_for_association_memberships(
        cls,
        current_month: datetime.date,
        cache: dict,
        generated_payments: set[Payment],
        member_id: str | None = None,
    ) -> list[Payment]:
        active_memberships = MonthPaymentBuilderUtils.filter_contracts_by_member(
            contracts=cls.get_active_memberships(
                cache=cache, first_of_month=current_month
            ),
            member_id=member_id,
        )

        memberships_by_member = cls.group_memberships_by_member(active_memberships)

        payments_to_create = []

        for (
            member,
            memberships,
        ) in memberships_by_member.items():
            rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
                member=member, reference_date=current_month, cache=cache
            )

            payment = MonthPaymentBuilderUtils.build_payment_for_contract_and_member(
                member=member,
                first_of_month=current_month,
                contracts=memberships,
                rhythm=rhythm,
                cache=cache,
                generated_payments=generated_payments,
                in_trial=False,
                payment_type=cls.PAYMENT_TYPE_ASSOCIATION_MEMBERSHIP,
                calculation_parts_function=cls.get_calculation_parts,
                allow_negative_amounts=False,
            )
            if payment is not None:
                payments_to_create.append(payment)

        return payments_to_create

    @classmethod
    def get_total_to_pay(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        contracts: list[AssociationMembership],
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
        contracts: list[AssociationMembership],
        cache: dict,
    ) -> list[CalculationPart]:
        memberships_active_within_period = sorted(
            (
                membership
                for membership in contracts
                if DateRangeOverlapChecker.do_ranges_overlap(
                    range_1_start=range_start,
                    range_1_end=range_end,
                    range_2_start=membership.start_date,
                    range_2_end=membership.end_date,
                )
            ),
            key=lambda membership: (membership.start_date, membership.type.name),
        )
        return [
            part
            for membership in memberships_active_within_period
            for part in cls._get_calculation_parts_for_single_membership_within_range(
                membership=membership,
                range_start=range_start,
                range_end=range_end,
                cache=cache,
            )
        ]

    @classmethod
    def get_active_memberships(
        cls, cache: dict, first_of_month: datetime.date
    ) -> list[AssociationMembership]:
        existing_memberships = TapirCache.get_all_association_memberships(cache=cache)

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
            membership
            for membership in existing_memberships
            if DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=membership.start_date,
                range_1_end=membership.end_date,
                range_2_start=range_start,
                range_2_end=range_end,
            )
        ]

    @classmethod
    def _get_calculation_parts_for_single_membership_within_range(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        membership: AssociationMembership,
        cache: dict,
    ) -> list[CalculationPart]:
        parts = []
        current_month = range_start
        while current_month < range_end:
            part = cls._build_calculation_part_for_membership_within_month(
                first_of_month=current_month, membership=membership, cache=cache
            )
            if part is not None:
                parts.append(part)
            current_month += relativedelta(months=1)

        return parts

    @classmethod
    def _build_calculation_part_for_membership_within_month(
        cls,
        first_of_month: datetime.date,
        membership: AssociationMembership,
        cache: dict,
    ) -> CalculationPart | None:
        nb_days_in_month = get_last_day_of_month(first_of_month).day
        nb_days_overlap = MonthPaymentBuilderUtils.get_number_of_days_covered_in_month(
            first_of_month=first_of_month,
            contract_start=membership.start_date,
            contract_end=membership.end_date,
        )
        if nb_days_overlap == 0:
            return None

        price = AssociationMembershipTypePriceGetter.get_price(
            membership_type=membership.type, reference_date=first_of_month, cache=cache
        )
        prefix = f"{date_format(first_of_month, "F Y")}, Vereinsmitgliedschaft {membership.type.name}"
        if nb_days_overlap == nb_days_in_month:
            return CalculationPart(
                explanation=f"{prefix}: {format_currency(price)} € monatlich (voller Monat)",
                value=price,
            )

        ratio = nb_days_overlap / nb_days_in_month
        value = (price * Decimal(ratio)).quantize(Decimal("0.01"))
        return CalculationPart(
            explanation=f"{prefix}: {format_currency(price)} € × {nb_days_overlap} von {nb_days_in_month} Tagen = {format_currency(value)} €",
            value=value,
        )

    @classmethod
    def group_memberships_by_member(
        cls, memberships: list[AssociationMembership]
    ) -> dict[Member, set[AssociationMembership]]:
        memberships_by_member: dict[Member, set[AssociationMembership]] = {}

        for membership in memberships:
            memberships_by_member.setdefault(membership.member, set()).add(membership)

        return memberships_by_member
