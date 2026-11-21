from decimal import Decimal

from django.db.models import OuterRef, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce

from tapir.accounts.models import TapirUser
from tapir.associations.models import AssociationMembership
from tapir.associations.services.association_deposit_settings import (
    association_deposits_enabled,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member, Payment


class AssociationDepositOverviewProvider:
    @staticmethod
    def can_view(user: TapirUser, cache: dict) -> bool:
        return user.has_perm(Permission.Coop.MANAGE) and association_deposits_enabled(
            cache
        )

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
        agreed = (
            payments.order_by()
            .values("association_deposit")
            .annotate(total=Sum("amount"))
        )
        exported = agreed.filter(transaction__isnull=False)
        return queryset.annotate(
            deposit_agreed=Coalesce(Subquery(agreed.values("total")), Decimal("0")),
            deposit_exported=Coalesce(Subquery(exported.values("total")), Decimal("0")),
        )
