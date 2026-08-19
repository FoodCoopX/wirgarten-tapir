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
                id="route_basket_totals",
                display_name="Kistenzahl pro Ausfahrrunde",
                description="Summen je Kistengröße bzw. Ernteanteil über alle Verteilstationen der Tour",
                get_value=cls.get_value_route_basket_totals,
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
    def get_value_route_basket_totals(
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
        pickup_location_data = []
        for pickup_location in pickup_locations:
            pickup_location_totals = pickup_location["global_values"]
            for header, value in pickup_location_totals.items():
                totals[header] += value
            pickup_location_data.append(
                {
                    "name": pickup_location["name"],
                    "totals": pickup_location_totals,
                }
            )

        convert_headers = (
            PickingModeProvider.get_picking_mode(cache=cache) == PICKING_MODE_SHARE
        )
        return {
            "calendar_week": reference_datetime.isocalendar().week,
            "headers": headers,
            "totals": totals,
            "pickup_location_data": pickup_location_data,
            "pickup_location_name_lines": cls.build_pickup_location_name_lines(
                [pickup_location["name"] for pickup_location in pickup_location_data]
            ),
            "convert_headers": convert_headers,
            "product_name_by_id": {
                product.id: product.name
                for product in TapirCache.get_all_products(cache=cache)
            },
        }

    @classmethod
    def add_across_route_aggregates(cls, entries: list[dict]) -> None:
        if not entries or not isinstance(entries[0], dict):
            return

        route_basket_totals_list = [
            entry["route_basket_totals"]
            for entry in entries
            if isinstance(entry.get("route_basket_totals"), dict)
        ]
        if not route_basket_totals_list:
            return

        headers = route_basket_totals_list[0].get("headers")
        if not headers:
            headers = list((route_basket_totals_list[0].get("totals") or {}).keys())
        totals_across_routes = dict.fromkeys(headers, 0)
        grand_total = 0
        for route_basket_totals in route_basket_totals_list:
            totals = route_basket_totals.get("totals") or {}
            for header in headers:
                value = totals.get(header) or 0
                totals_across_routes[header] += value
                grand_total += value

        for route_basket_totals in route_basket_totals_list:
            route_basket_totals["totals_across_routes"] = totals_across_routes
            route_basket_totals["grand_total"] = grand_total

    @classmethod
    def build_pickup_location_name_lines(cls, names: list[str]) -> list[str]:
        if not names:
            return []
        if len(names) < 4:
            return [", ".join(names)]
        midpoint = (len(names) + 1) // 2
        return [f"{', '.join(names[:midpoint])},", ", ".join(names[midpoint:])]
