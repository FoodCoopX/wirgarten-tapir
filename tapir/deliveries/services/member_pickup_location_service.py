import datetime

from django.db.models import QuerySet, OuterRef, Subquery

from tapir.wirgarten.models import Member, MemberPickupLocation


class MemberPickupLocationService:
    @classmethod
    def annotate_member_queryset_with_pickup_location_at_date(
        cls, queryset: QuerySet[Member], reference_date: datetime.date
    ) -> QuerySet[Member]:
        current_member_pickup_location = (
            MemberPickupLocation.objects.filter(
                member=OuterRef("id"), valid_from__lte=reference_date
            )
            .order_by("-valid_from")
            .values("pickup_location_id")[:1]
        )

        return queryset.annotate(
            current_pickup_location_id=Subquery(current_member_pickup_location)
        )
