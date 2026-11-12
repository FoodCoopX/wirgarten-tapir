from decimal import Decimal

from django.db.models import Exists, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce

from tapir.associations.models import AssociationDeposit
from tapir.associations.services.association_deposit_settings import (
    association_deposits_enabled,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Payment


class AssociationDepositOverviewProvider:
    @staticmethod
    def can_view(user, cache: dict) -> bool:
        return user.has_perm(Permission.Coop.MANAGE) and association_deposits_enabled(
            cache
        )

    @classmethod
    def annotate_members(cls, members, cache: dict):
        return cls._annotate(members, member_id=OuterRef("pk"))

    @classmethod
    def annotate_memberships(cls, memberships):
        return cls._annotate(memberships, member_id=OuterRef("member_id"))

    @staticmethod
    def _annotate(queryset, member_id):
        payments = Payment.objects.filter(association_deposit__member_id=member_id)
        agreed = (
            payments.order_by()
            .values("association_deposit")
            .annotate(total=Sum("amount"))
        )
        exported = agreed.filter(transaction__isnull=False)
        deposits = AssociationDeposit.objects.filter(member_id=member_id)
        opening_balance = Coalesce(
            Subquery(deposits.values("opening_balance")), Decimal("0")
        )
        outstanding = Coalesce(
            Subquery(deposits.values("imported_outstanding_amount")), Decimal("0")
        )
        return queryset.annotate(
            deposit_imported_outstanding=outstanding,
            deposit_agreement_requested=Exists(
                deposits.filter(payments__isnull=True, opening_balance__isnull=True)
            ),
            deposit_agreed=Coalesce(Subquery(agreed.values("total")), Decimal("0"))
            + opening_balance
            + outstanding,
            deposit_exported=Coalesce(Subquery(exported.values("total")), Decimal("0"))
            + opening_balance,
        )
