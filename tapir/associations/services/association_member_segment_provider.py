import datetime

from django.db.models import QuerySet

from tapir.associations.models import AssociationMembership
from tapir.wirgarten.models import Member
from tapir.wirgarten.service.products import get_today


class AssociationMemberSegmentProvider:
    @staticmethod
    def get_queryset_with_association_membership(
        reference_date: datetime.date | None = None,
    ) -> QuerySet:
        if reference_date is None:
            reference_date = get_today()

        return Member.objects.filter(
            id__in=AssociationMembership.objects.active_at(reference_date).values(
                "member_id"
            )
        ).distinct()

    @staticmethod
    def get_queryset_without_association_membership(
        reference_date: datetime.date | None = None,
    ) -> QuerySet:
        return Member.objects.exclude(
            id__in=AssociationMemberSegmentProvider.get_queryset_with_association_membership(
                reference_date
            )
        ).distinct()
