import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from tapir.associations.models import AssociationMembership
from tapir.associations.services.association_membership_price_type_getter import (
    AssociationMembershipTypePriceGetter,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_last_day_of_month, get_first_of_next_month
from tapir.wirgarten.models import (
    Payment,
    Member,
)


class MonthPaymentBuilderAssociationMembership:
    PAYMENT_TYPE_ASSOCIATION_MEMBERSHIP = "payment_type_association_membership"

    @classmethod
    def build_payments_for_association_memberships(
        cls,
        current_month: datetime.date,
        cache: dict,
        generated_payments: set[Payment],
    ) -> list[Payment]:
        active_memberships = cls.get_active_memberships(
            cache=cache, first_of_month=current_month
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
                total_to_pay_function=cls.get_total_to_pay,
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
        memberships_active_within_period = [
            membership
            for membership in contracts
            if DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=membership.start_date,
                range_1_end=membership.end_date,
                range_2_start=range_start,
                range_2_end=range_end,
            )
        ]
        total_to_pay = sum(
            [
                cls.get_amount_for_single_membership_within_range(
                    membership=membership,
                    range_start=range_start,
                    range_end=range_end,
                    cache=cache,
                )
                for membership in memberships_active_within_period
            ],
            Decimal(0),
        )
        return total_to_pay

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
    def get_amount_for_single_membership_within_range(
        cls,
        range_start: datetime.date,
        range_end: datetime.date,
        membership: AssociationMembership,
        cache: dict,
    ) -> Decimal:
        current_month = range_start
        total = Decimal(0)

        while current_month < range_end:
            total += cls.get_amount_to_pay_for_membership_within_month(
                first_of_month=current_month, membership=membership, cache=cache
            )

            current_month += relativedelta(months=1)

        return total

    @classmethod
    def get_amount_to_pay_for_membership_within_month(
        cls,
        first_of_month: datetime.date,
        membership: AssociationMembership,
        cache: dict,
    ):
        nb_days_in_month = (
            get_first_of_next_month(first_of_month) - first_of_month
        ).days
        nb_days_overlap = DateRangeOverlapChecker.get_number_of_days_of_overlap(
            range_1_start=membership.start_date,
            range_1_end=membership.end_date,
            range_2_start=first_of_month,
            range_2_end=get_last_day_of_month(first_of_month),
        )
        ratio = nb_days_overlap / nb_days_in_month

        price = AssociationMembershipTypePriceGetter.get_price(
            membership_type=membership.type, reference_date=first_of_month, cache=cache
        )

        return (price * Decimal(ratio)).quantize(Decimal("0.01"))

    @classmethod
    def group_memberships_by_member(
        cls, memberships: list[AssociationMembership]
    ) -> dict[Member, set[AssociationMembership]]:
        memberships_by_member: dict[Member, set[AssociationMembership]] = {}

        for membership in memberships:
            memberships_by_member.setdefault(membership.member, set()).add(membership)

        return memberships_by_member
