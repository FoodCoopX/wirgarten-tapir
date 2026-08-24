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
                    "show_details_in_basket_totals_export": pickup_location[
                        "show_details_in_basket_totals_export"
                    ],
                }
            )

        convert_headers = (
            PickingModeProvider.get_picking_mode(cache=cache) == PICKING_MODE_SHARE
        )
        result = {
            "calendar_week": reference_datetime.isocalendar().week,
            "headers": headers,
            "totals": totals,
            "pickup_location_data": pickup_location_data,
            "pickup_location_name_lines": cls.build_pickup_location_name_lines(
                [
                    pickup_location["name"]
                    for pickup_location in pickup_location_data
                    if not pickup_location["show_details_in_basket_totals_export"]
                ]
            ),
            "convert_headers": convert_headers,
            "product_name_by_id": {
                product.id: product.name
                for product in TapirCache.get_all_products(cache=cache)
            },
        }
        cls.add_across_route_aggregates(cache=cache, route_basket_totals=result)
        return result

    @classmethod
    def add_across_route_aggregates(
        cls, cache: dict, route_basket_totals: dict
    ) -> None:
        accumulator = cache.setdefault(
            "across_route_basket_totals",
            {
                "first": None,
                "totals_across_routes": None,
                "grand_total": 0,
            },
        )

        headers = route_basket_totals.get("headers")
        if not headers:
            headers = list((route_basket_totals.get("totals") or {}).keys())

        if accumulator["totals_across_routes"] is None:
            accumulator["totals_across_routes"] = dict.fromkeys(headers, 0)

        totals = route_basket_totals.get("totals") or {}
        for header in accumulator["totals_across_routes"]:
            value = totals.get(header) or 0
            accumulator["totals_across_routes"][header] += value
            accumulator["grand_total"] += value

        if accumulator["first"] is None:
            accumulator["first"] = route_basket_totals
            route_basket_totals["totals_across_routes"] = accumulator[
                "totals_across_routes"
            ]

        accumulator["first"]["grand_total"] = accumulator["grand_total"]

    @classmethod
    def build_pickup_location_name_lines(cls, names: list[str]) -> list[str]:
        if not names:
            return []
        if len(names) < 4:
            return [", ".join(names)]
        midpoint = (len(names) + 1) // 2
        return [f"{', '.join(names[:midpoint])},", ", ".join(names[midpoint:])]
