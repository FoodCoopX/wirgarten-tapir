from django.db.models import QuerySet

from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.pickup_locations.services.pickup_location_column_provider import (
    PickupLocationColumnProvider,
)
from tapir.wirgarten.models import PickupLocation


class PickupLocationSegmentProvider:
    @classmethod
    def get_pickup_location_segments(cls):
        return [
            ExportSegment(
                id="pickup_locations.all",
                display_name="Alle Abholorte",
                description="",
                get_queryset=cls.get_queryset_all_pickup_stations,
                get_available_columns=PickupLocationColumnProvider.get_pickup_location_columns,
            ),
        ]

    @classmethod
    def get_queryset_all_pickup_stations(cls, _) -> QuerySet:
        return PickupLocation.objects.all().order_by("name")
