import datetime

from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
from tapir.pickup_locations.services.pickup_location_data_for_location_route_builder import (
    PickupLocationDataForLocationRouteBuilder,
)
from tapir.wirgarten.models import PickupLocation, LocationRoute


class LocationRouteColumnProvider:
    @classmethod
    def get_location_route_columns(cls):
        return [
            ExportSegmentColumn(
                id="route_name",
                display_name="Ausfahrrunde",
                description="",
                get_value=cls.get_value_route_name,
            ),
            ExportSegmentColumn(
                id="pickup_locations",
                display_name="Abholorte",
                description="",
                get_value=cls.get_value_pickup_locations,
            ),
        ]

    @classmethod
    def get_value_route_name(cls, route: LocationRoute | None, _, __):
        if not route:
            return ""
        return route.name

    @classmethod
    def get_value_pickup_locations(
        cls,
        route: LocationRoute | None,
        reference_datetime: datetime.datetime,
        cache: dict,
    ):
        return [
            PickupLocationDataForLocationRouteBuilder.build_data_for_location_route(
                pickup_location=pickup_location,
                reference_datetime=reference_datetime,
                cache=cache,
            )
            for pickup_location in PickupLocation.objects.filter(
                location_route=route
            ).order_by("name")
        ]
