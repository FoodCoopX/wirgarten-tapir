from tapir.pickup_locations.services.pickup_location_column_provider import (
    PickupLocationColumnProvider,
)
import datetime

from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
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
        locations = []
        for location in PickupLocation.objects.filter(location_route=route):
            subscriptions = PickupLocationColumnProvider.get_value_pickup_location_deliveries_current_week(
                location, reference_datetime, cache
            )

            locations.append(
                {
                    "name": location.name,
                    "street": location.street,
                    "street_2": location.street_2,
                    "postcode": location.postcode,
                    "city": location.city,
                    "route_info": location.route_info,
                    "subscriptions": subscriptions,
                }
            )
        return locations
