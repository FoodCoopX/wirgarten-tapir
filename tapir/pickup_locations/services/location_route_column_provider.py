from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.pickup_locations.config import PICKING_MODE_BASKET
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
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
            subscriptions = PickupLocationColumnProvider.get_subscriptions_with_deliveries_current_week(
                location, reference_datetime, cache
            )

            use_basket = (
                get_parameter_value(ParameterKeys.PICKING_MODE, cache=cache)
                == PICKING_MODE_BASKET
            )
            baskets = {}
            equivalences = dict.fromkeys(
                BasketSizeCapacitiesService.get_basket_sizes(cache=cache), 0
            )

            def product_to_basket(product, quantity):
                if not use_basket:
                    return [
                        {
                            "name": str(product),
                            "quantity": quantity,
                        }
                    ]
                if product not in baskets:
                    baskets[product] = [
                        {
                            "name": e.basket_size_name,
                            "quantity": e.quantity,
                        }
                        for e in ProductBasketSizeEquivalence.objects.filter(
                            product=product
                        )
                        if e.basket_size_name in equivalences and e.quantity > 0
                    ]
                if not baskets[product]:
                    # no equivalence: return original product
                    return [
                        {
                            "name": str(product),
                            "quantity": quantity,
                        }
                    ]

                return [
                    {"name": e["name"], "quantity": e["quantity"] * quantity}
                    for e in baskets[product]
                ]

            locations.append(
                {
                    "name": location.name,
                    "street": location.street,
                    "street_2": location.street_2,
                    "postcode": location.postcode,
                    "city": location.city,
                    "route_info": location.route_info,
                    "subscriptions": [
                        {
                            "member_no": subscription.member.member_no,
                            "last_name": subscription.member.last_name,
                            "first_name": subscription.member.first_name,
                            "phone_number": subscription.member.phone_number,
                            "email": subscription.member.email,
                            "products": product_to_basket(
                                subscription.product, subscription.quantity
                            ),
                        }
                        for subscription in subscriptions
                    ],
                }
            )

        return locations
