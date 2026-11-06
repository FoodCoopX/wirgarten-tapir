import datetime

from tapir.associations.models import AssociationDepositAccount, AssociationMembership
from tapir.wirgarten.models import Payment
from tapir.wirgarten.utils import get_today
from tapir.utils.shortcuts import get_from_cache_or_compute


class AssociationDepositMembershipCoverage:
    CACHE_KEY = "association_deposit_membership_periods"

    @classmethod
    def get_periods(cls, member, cache: dict) -> list[tuple]:
        by_member = get_from_cache_or_compute(cache, cls.CACHE_KEY, dict)
        return get_from_cache_or_compute(
            by_member, member.pk, lambda: cls._read_periods(member, cache)
        )

    @classmethod
    def invalidate_member(cls, member, cache: dict):
        cache.get(cls.CACHE_KEY, {}).pop(member.pk, None)
        cache.pop("all_association_memberships", None)
        for key in [
            "association_memberships_by_member_id",
            "association_memberships_by_member_id_and_date",
        ]:
            cache.pop(key, None)

    @staticmethod
    def _read_periods(member, cache: dict) -> list[tuple]:
        return AssociationDepositMembershipCoverage.merge_periods(
            AssociationMembership.objects.filter(member=member)
            .order_by("start_date", "pk")
            .values_list("start_date", "end_date")
        )

    @staticmethod
    def merge_periods(memberships) -> list[tuple]:
        periods = []
        for start, end in memberships:
            end = end or datetime.date.max
            if periods and (start - periods[-1][1]).days <= 1:
                periods[-1] = (periods[-1][0], max(end, periods[-1][1]))
            else:
                periods.append((start, end))
        return periods

    @classmethod
    def get_agreement_period(cls, account: AssociationDepositAccount, cache: dict):
        periods = cls.get_periods(account.member, cache)
        return next(
            (
                period
                for period in periods
                if account.effective_from is None or period[1] >= account.effective_from
            ),
            periods[-1] if periods else None,
        )

    @classmethod
    def get_collection_cutoff(cls, account: AssociationDepositAccount, cache: dict):
        period = cls.get_agreement_period(account, cache)
        end = period[1] if period else datetime.date.max
        boundary = end + datetime.timedelta(days=1) if end < datetime.date.max else None
        return min(
            (day for day in [boundary, account.collection_stopped_from] if day),
            default=None,
        )

    @classmethod
    def requires_new_agreement(cls, account: AssociationDepositAccount, cache: dict):
        cutoff = cls.get_collection_cutoff(account, cache)
        return cutoff is not None and any(
            end >= cutoff for _, end in cls.get_periods(account.member, cache)
        )

    @classmethod
    def can_collect_on(cls, account, due_date, collection_date, cache: dict) -> bool:
        period = cls.get_agreement_period(account, cache)
        cutoff = cls.get_collection_cutoff(account, cache)
        return bool(
            period
            and not account.refund_requires_agreement
            and period[0] <= due_date <= period[1]
            and period[0] <= collection_date <= period[1]
            and (cutoff is None or max(due_date, collection_date) < cutoff)
        )

    @classmethod
    def filter_upcoming_payments(
        cls, payments: set[Payment], cache: dict
    ) -> set[Payment]:
        return {
            payment
            for payment in payments
            if payment.association_deposit_account_id is None
            or payment.transaction_id is not None
            or payment.status != Payment.PaymentStatus.DUE
            or cls.can_collect_on(
                payment.association_deposit_account,
                payment.due_date,
                max(payment.due_date, get_today(cache)),
                cache,
            )
        }
