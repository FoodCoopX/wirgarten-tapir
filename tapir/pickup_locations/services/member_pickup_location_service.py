import datetime

from django.db.models import QuerySet, OuterRef, Subquery

from tapir.wirgarten.models import Member, MemberPickupLocation


class MemberPickupLocationService:
    ANNOTATION_CURRENT_PICKUP_LOCATION_ID = "current_pickup_location_id"

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
            **{
                cls.ANNOTATION_CURRENT_PICKUP_LOCATION_ID: Subquery(
                    current_member_pickup_location
                )
            }
        )

    @classmethod
    def get_member_pickup_location_id(
        cls, member: Member, reference_date: datetime.date
    ) -> int | None:
        if not hasattr(member, cls.ANNOTATION_CURRENT_PICKUP_LOCATION_ID):
            member = cls.annotate_member_queryset_with_pickup_location_at_date(
                Member.objects.filter(id=member.id), reference_date
            ).get()

        return getattr(member, cls.ANNOTATION_CURRENT_PICKUP_LOCATION_ID)
