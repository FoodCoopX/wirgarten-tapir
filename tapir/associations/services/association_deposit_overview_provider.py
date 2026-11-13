from decimal import Decimal

from django.db.models import Case, Exists, OuterRef, Q, Subquery, Sum, When
from django.db.models.functions import Coalesce

from tapir.associations.models import AssociationDeposit, AssociationMembership
from tapir.associations.services.association_deposit_settings import (
    association_deposits_enabled,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.utils import get_today


class AssociationDepositOverviewProvider:
    @staticmethod
    def can_view(user, cache: dict) -> bool:
        return user.has_perm(Permission.Coop.MANAGE) and association_deposits_enabled(
            cache
        )

    @classmethod
    def annotate_members(cls, members, cache: dict):
        membership = cls.memberships_with_deposits(OuterRef("pk"), cache)
        members = members.alias(
            deposit_membership_id=Subquery(membership.values("pk")[:1])
        )
        return cls._annotate(members, OuterRef("deposit_membership_id"))

    @staticmethod
    def memberships_with_deposits(member_id, cache: dict):
        today = get_today(cache=cache)
        return (
            AssociationMembership.objects.filter(member_id=member_id)
            .filter(
                Exists(AssociationDeposit.objects.filter(membership_id=OuterRef("pk")))
            )
            .filter(Q(end_date=None) | Q(end_date__gte=today))
            .order_by(
                Case(When(start_date__lte=today, then=0), default=1),
                "-start_date",
                "-pk",
            )
        )

    @classmethod
    def annotate_memberships(cls, memberships):
        return cls._annotate(memberships, OuterRef("pk"))

    @staticmethod
    def agreed_amount():
        return Sum("payment__amount", default=0)

    @classmethod
    def _annotate(cls, queryset, membership_id):
        deposits = AssociationDeposit.objects.filter(membership_id=membership_id)
        exported = deposits.filter(payment__transaction__isnull=False)
        return queryset.annotate(
            deposit_agreed=Coalesce(
                Subquery(
                    deposits.order_by()
                    .values("membership_id")
                    .annotate(total=Sum("payment__amount"))
                    .values("total")
                ),
                Decimal("0"),
            ),
            deposit_exported=Coalesce(
                Subquery(
                    exported.order_by()
                    .values("membership_id")
                    .annotate(total=Sum("payment__amount"))
                    .values("total")
                ),
                Decimal("0"),
            ),
        )
