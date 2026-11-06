from collections import defaultdict
from decimal import Decimal

from tapir.associations.models import AssociationDepositAccount
from tapir.associations.services.association_deposit_membership_coverage import (
    AssociationDepositMembershipCoverage,
)
from tapir.associations.services.association_deposit_overview_provider import (
    AssociationDepositOverviewProvider,
)
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.utils import get_today


class AssociationDepositDepartureReportProvider:
    @classmethod
    def get_report(cls, year: int, cache: dict) -> dict:
        rows = cls.get_cohorts(cache).get(year, [])
        return {
            "year": year,
            "as_of": get_today(cache),
            "rows": rows,
            "member_count": len(rows),
            "retained_amount": sum(
                (row["retained_amount"] for row in rows), Decimal("0")
            ),
        }

    @classmethod
    def get_dashboard_data(cls, cache: dict) -> dict:
        return {
            "as_of": get_today(cache),
            "default_year": get_today(cache).year - 1,
            "cohorts": [
                cls.get_report(year, cache)
                for year in sorted(cls.get_cohorts(cache), reverse=True)
            ],
            "overall_retained_amount": sum(
                (
                    row["retained_amount"]
                    for row in AssociationDepositOverviewProvider.get_rows(
                        cache
                    ).values()
                ),
                Decimal("0"),
            ),
        }

    @classmethod
    def get_cohorts(cls, cache: dict) -> dict:
        return get_from_cache_or_compute(
            cache,
            "association_deposit_departure_cohorts",
            lambda: cls._read_cohorts(cache),
        )

    @staticmethod
    def _read_cohorts(cache: dict) -> dict:
        today = get_today(cache)
        details = AssociationDepositOverviewProvider.get_rows(cache)
        cohorts = defaultdict(list)
        for account in AssociationDepositAccount.objects.select_related(
            "member"
        ).order_by("member__member_no", "member_id"):
            periods = AssociationDepositMembershipCoverage.get_periods(
                account.member, cache
            )
            if not periods or periods[-1][1] >= today:
                continue
            departure = periods[-1][1]
            cohorts[departure.year].append(
                {
                    **details[account.member_id],
                    "member": account.member,
                    "departure_date": departure,
                }
            )
        return dict(cohorts)
