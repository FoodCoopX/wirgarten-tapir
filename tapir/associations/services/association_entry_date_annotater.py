from django.db.models import QuerySet, OuterRef, Subquery

from tapir.associations.models import AssociationMembership
from tapir.wirgarten.models import Member


class AssociationEntryDateAnnotater:
    ANNOTATION_ASSOCIATION_ENTRY_DATE = "association_entry_date"

    @classmethod
    def annotate_queryset_with_association_entry_date(cls, queryset: QuerySet[Member]):
        earliest_membership_start_date = (
            AssociationMembership.objects.filter(member_id=OuterRef("id"))
            .order_by("start_date")
            .values("start_date")[:1]
        )

        return queryset.annotate(
            **{
                cls.ANNOTATION_ASSOCIATION_ENTRY_DATE: Subquery(
                    earliest_membership_start_date
                )
            }
        )
