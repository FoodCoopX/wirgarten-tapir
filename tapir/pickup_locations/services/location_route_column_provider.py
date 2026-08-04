import datetime

from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
from tapir.pickup_locations.config import PICKING_MODE_SHARE
from tapir.pickup_locations.services.picking_mode_provider import PickingModeProvider
from tapir.pickup_locations.services.pickup_location_data_for_location_route_builder import (
    PickupLocationDataForLocationRouteBuilder,
)
from tapir.utils.services.tapir_cache import TapirCache
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
            ExportSegmentColumn(
                id="route_crate_totals",
                display_name="Kistenzahl pro Ausfahrrunde",
                description="Summen je Kistengröße bzw. Ernteanteil über alle Verteilstationen der Tour",
                get_value=cls.get_value_route_crate_totals,
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

    @classmethod
    def get_value_route_crate_totals(
        cls,
        route: LocationRoute | None,
        reference_datetime: datetime.datetime,
        cache: dict,
    ):
        pickup_locations = cls.get_value_pickup_locations(
            route=route,
            reference_datetime=reference_datetime,
            cache=cache,
        )
        headers = PickupLocationDataForLocationRouteBuilder.get_headers(
            cache=cache, reference_date=reference_datetime.date()
        )
        totals = dict.fromkeys(headers, 0)
        stations = []
        for pickup_location in pickup_locations:
            station_totals = pickup_location["global_values"]
            for header, value in station_totals.items():
                totals[header] = totals.get(header, 0) + value
            stations.append(
                {
                    "name": pickup_location["name"],
                    "totals": station_totals,
                }
            )

        convert_headers = (
            PickingModeProvider.get_picking_mode(cache=cache) == PICKING_MODE_SHARE
        )
        return {
            "calendar_week": reference_datetime.isocalendar().week,
            "headers": headers,
            "totals": totals,
            "stations": stations,
            "convert_headers": convert_headers,
            "product_name_by_id": {
                product.id: product.name
                for product in TapirCache.get_all_products(cache=cache)
            },
        }
