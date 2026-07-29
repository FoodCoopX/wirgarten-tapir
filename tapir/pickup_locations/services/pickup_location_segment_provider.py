from tapir.pickup_locations.services.location_route_column_provider import (
    LocationRouteColumnProvider,
)
from django.db.models import QuerySet

from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.pickup_locations.services.pickup_location_column_provider import (
    PickupLocationColumnProvider,
)
from tapir.wirgarten.models import PickupLocation, LocationRoute


class PickupLocationSegmentProvider:
    SEGMENT_ID_ALL_PICKUP_LOCATIONS = "pickup_locations.all"
    SEGMENT_ID_ALL_LOCATION_ROUTES = "pickup_locations.routes"

    @classmethod
    def get_pickup_location_segments(cls):
        return [
            ExportSegment(
                id=cls.SEGMENT_ID_ALL_PICKUP_LOCATIONS,
                display_name="Alle Abholorte",
                description="",
                get_queryset=cls.get_queryset_all_pickup_stations,
                get_available_columns=PickupLocationColumnProvider.get_pickup_location_columns,
            ),
            ExportSegment(
                id=cls.SEGMENT_ID_ALL_LOCATION_ROUTES,
                display_name="Alle Ausfahrrunden",
                description="",
                get_queryset=cls.get_queryset_all_location_routes,
                get_available_columns=LocationRouteColumnProvider.get_location_route_columns,
            ),
        ]

    @classmethod
    def get_queryset_all_pickup_stations(cls, _) -> QuerySet:
        return PickupLocation.objects.all().order_by("name")

    @classmethod
    def get_queryset_all_location_routes(cls, _) -> QuerySet:
        yield from LocationRoute.objects.all().order_by("name")
        # append a None if some locations are not affected to a route
        if PickupLocation.objects.filter(location_route__isnull=True).exists():
            yield None
