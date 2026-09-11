import datetime

from django.db.models import QuerySet, OuterRef, Subquery
from django.db.models.functions import Extract

from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_column_provider import JokerColumnProvider
from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.wirgarten.models import GrowingPeriod, MemberPickupLocation


class JokerSegmentProvider:
    SEGMENT_ID_JOKER_THIS_GROWING_PERIOD = "jokers.this_growing_period"

    @classmethod
    def get_joker_segments(cls):
        return [
            ExportSegment(
                id=cls.SEGMENT_ID_JOKER_THIS_GROWING_PERIOD,
                display_name="Alle Joker",
                description="Alle eingesetzte Joker in der Vertragsperiode, sortiert nach Woche und Abholort",
                get_queryset=cls.get_queryset_all_joker_this_growing_period,
                get_available_columns=JokerColumnProvider.get_joker_columns,
            ),
        ]

    @classmethod
    def get_queryset_all_joker_this_growing_period(
        cls, reference_datetime: datetime.datetime
    ) -> QuerySet[Joker]:
        growing_period = GrowingPeriod.objects.filter(
            start_date__lte=reference_datetime.date(),
            end_date__gte=reference_datetime.date(),
        ).first()
        if not growing_period:
            return Joker.objects.none()

        jokers = Joker.objects.filter(
            date__gte=growing_period.start_date,
            date__lte=growing_period.end_date,
        ).select_related("member")

        jokers = jokers.annotate(calendar_week=Extract("date", "week"))
        jokers = cls.annotate_joker_queryset_with_pickup_location_name(jokers)

        return jokers.order_by("calendar_week", "pickup_location_name")

    @classmethod
    def annotate_joker_queryset_with_pickup_location_name(
        cls, queryset: QuerySet[Joker]
    ) -> QuerySet[Joker]:
        current_member_pickup_location = (
            MemberPickupLocation.objects.filter(
                member=OuterRef("member_id"), valid_from__lte=OuterRef("date")
            )
            .order_by("-valid_from")
            .values("pickup_location__name")[:1]
        )

        return queryset.annotate(
            pickup_location_name=Subquery(current_member_pickup_location)
        )
