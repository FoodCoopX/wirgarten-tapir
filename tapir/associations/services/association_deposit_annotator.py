from decimal import Decimal

from django.db.models import Exists, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce

from tapir.associations.models import (
    AssociationDepositTransaction,
    AssociationMembership,
)
from tapir.wirgarten.models import Member, Payment


class AssociationDepositAnnotator:
    @classmethod
    def annotate_members(cls, members: QuerySet[Member]) -> QuerySet[Member]:
        return cls._annotate(members, member_id=OuterRef("pk"))

    @classmethod
    def annotate_memberships(
        cls, memberships: QuerySet[AssociationMembership]
    ) -> QuerySet[AssociationMembership]:
        return cls._annotate(memberships, member_id=OuterRef("member_id"))

    @staticmethod
    def _annotate(queryset: QuerySet, member_id: OuterRef) -> QuerySet:
        transactions = AssociationDepositTransaction.objects.filter(member_id=member_id)
        agreed = transactions.values("member").annotate(total=Sum("amount"))
        exported_payment = Payment.objects.filter(
            association_deposit_transaction_id=OuterRef("pk"), transaction__isnull=False
        )
        received = (
            transactions.annotate(exported=Exists(exported_payment))
            .filter(
                ~Q(transaction_type=AssociationDepositTransaction.Type.SUBSCRIPTION)
                | Q(exported=True)
            )
            .values("member")
            .annotate(total=Sum("amount"))
        )
        return queryset.annotate(
            deposit_agreed=Coalesce(Subquery(agreed.values("total")), Decimal("0")),
            deposit_exported=Coalesce(Subquery(received.values("total")), Decimal("0")),
        )
