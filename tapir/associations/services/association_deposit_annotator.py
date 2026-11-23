from decimal import Decimal

from django.db.models import Exists, OuterRef, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce

from tapir.associations.models import AssociationDeposit, AssociationMembership
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
        payments = Payment.objects.filter(association_deposit__member_id=member_id)
        agreed = payments.values("association_deposit").annotate(total=Sum("amount"))
        exported = agreed.filter(transaction__isnull=False)
        return queryset.annotate(
            deposit_agreement_requested=Exists(
                AssociationDeposit.objects.filter(
                    member_id=member_id, payments__isnull=True
                )
            ),
            deposit_agreed=Coalesce(Subquery(agreed.values("total")), Decimal("0")),
            deposit_exported=Coalesce(Subquery(exported.values("total")), Decimal("0")),
        )
