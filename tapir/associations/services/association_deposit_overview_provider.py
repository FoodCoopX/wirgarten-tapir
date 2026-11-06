from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositReceipt,
    AssociationDepositRefund,
    AssociationMembership,
)
from tapir.associations.services.association_deposit_balance_calculator import (
    AssociationDepositBalanceCalculator,
)
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.associations.services.association_deposit_membership_coverage import (
    AssociationDepositMembershipCoverage,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Payment
from tapir.wirgarten.utils import get_today, legal_status_is_association


class AssociationDepositOverviewProvider:
    STATES = {
        "not_agreed": "Noch kein Betrag vereinbart",
        "pending": "Individuelle Vereinbarung offen",
        "waived": "Vollständiger Verzicht vereinbart",
        "individual": "Individuelle Vereinbarung",
        "regular": "Reguläre Vereinbarung",
        "agreement_required": "Einzug bis zu neuer Vereinbarung gesperrt",
        "collection_stopped": "Einzug gestoppt",
    }
    COLUMNS = {
        "state_label": "Status",
        "agreed_amount": "Vereinbart (€)",
        "received_amount": "Extern eingegangen (€)",
        "committed_amount": "Verbucht / exportiert (€)",
        "pending_amount": "Offene Raten (€)",
        "stopped_amount": "Gestoppte Raten (€)",
        "refunded_amount": "Extern zurückgezahlt (€)",
        "retained_amount": "Rechnerischer Buchungsrest (€)",
        "overpayment_credit": "Überzahlung / Guthaben (€)",
    }

    @staticmethod
    def can_view(actor, cache: dict) -> bool:
        return legal_status_is_association(cache=cache) and (
            actor.has_perm(Permission.Coop.VIEW)
            or actor.has_perm(Permission.Coop.MANAGE)
        )

    @classmethod
    def get_rows(cls, cache: dict) -> dict:
        return get_from_cache_or_compute(
            cache, "association_deposit_overview", lambda: cls._read_rows(cache)
        )

    @classmethod
    def get_row(cls, member, cache: dict) -> dict:
        return cls.get_rows(cache).get(member.pk, cls._empty_row())

    @classmethod
    def filter_members(cls, queryset, value: str, cache: dict):
        rows = cls.get_rows(cache)
        if value == "minimum_outstanding":
            return queryset.filter(
                pk__in=[
                    pk
                    for pk, row in rows.items()
                    if not row["refund_requires_agreement"]
                    and row["required_amount"] is not None
                    and row["retained_amount"] < row["required_amount"]
                ]
            )
        if value == "not_agreed":
            return queryset.exclude(
                pk__in=[pk for pk, row in rows.items() if row["state"] != value]
            )
        return queryset.filter(
            pk__in=[pk for pk, row in rows.items() if row["state"] == value]
        )

    @classmethod
    def _empty_row(cls) -> dict:
        return {
            **dict.fromkeys(cls.COLUMNS, Decimal("0")),
            "agreed_amount": None,
            "overpayment_credit": None,
            "state": "not_agreed",
            "state_label": cls.STATES["not_agreed"],
        }

    @classmethod
    def _read_rows(cls, cache: dict) -> dict:
        today = get_today(cache)
        minimum = Decimal(str(AssociationDepositPolicy.get_settings(cache)["minimum"]))
        accounts = list(AssociationDepositAccount.objects.select_related("member"))
        payments = defaultdict(list)
        for payment in (
            Payment.objects.filter(association_deposit_account__isnull=False)
            .order_by("due_date", "pk")
            .values(
                "id",
                "association_deposit_account_id",
                "amount",
                "due_date",
                "instalment_number",
                "status",
                "transaction_id",
            )
        ):
            payments[payment.pop("association_deposit_account_id")].append(payment)
        received = dict(
            AssociationDepositReceipt.objects.filter(received_on__lte=today)
            .values("account_id")
            .annotate(total=Sum("amount"))
            .values_list("account_id", "total")
        )
        refunded = dict(
            AssociationDepositRefund.objects.filter(refunded_on__lte=today)
            .values("account_id")
            .annotate(total=Sum("amount"))
            .values_list("account_id", "total")
        )
        memberships = defaultdict(list)
        for member_id, start, end in AssociationMembership.objects.order_by(
            "start_date", "pk"
        ).values_list("member_id", "start_date", "end_date"):
            memberships[member_id].append((start, end))
        coverage = cache.setdefault(AssociationDepositMembershipCoverage.CACHE_KEY, {})
        rows = {}
        for account in accounts:
            periods = memberships[account.member_id]
            coverage[account.member_id] = (
                AssociationDepositMembershipCoverage.merge_periods(periods)
            )
            entries = payments[account.pk]
            committed = sum(
                (
                    p["amount"]
                    for p in entries
                    if p["transaction_id"] is not None
                    or p["status"] == Payment.PaymentStatus.PAID
                ),
                Decimal("0"),
            )
            balance = AssociationDepositBalanceCalculator.from_totals(
                received.get(account.pk, Decimal("0")),
                committed,
                refunded.get(account.pk, Decimal("0")),
            )
            details = AssociationDepositDetailsProvider.build_details(
                account,
                balance,
                entries,
                any(end is None or end >= today for _, end in periods),
                cache,
            )
            rows[account.member_id] = {
                **details,
                "required_amount": (
                    account.agreed_amount
                    if account.is_individual_agreement or account.agreed_amount is None
                    else min(account.agreed_amount, minimum)
                ),
                "state_label": cls.STATES[details["state"]],
            }
        return rows
