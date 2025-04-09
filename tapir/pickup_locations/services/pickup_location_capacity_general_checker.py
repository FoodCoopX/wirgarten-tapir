import datetime
from typing import Dict

from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.config import PICKING_MODE_SHARE, PICKING_MODE_BASKET
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_basket_checker import (
    PickupLocationCapacityModeBasketChecker,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    Product,
)
from tapir.wirgarten.parameters import Parameter


class PickupLocationCapacityGeneralChecker:
    @classmethod
    def does_pickup_location_have_enough_capacity_to_add_subscriptions(
        cls,
        pickup_location: PickupLocation,
        ordered_products_to_quantity_map: Dict[Product, int],
        already_registered_member: Member | None,
        subscription_start: datetime.date,
        cache: Dict,
    ) -> bool:

        if (
            already_registered_member
            and MemberPickupLocationService.get_member_pickup_location_id(
                already_registered_member, subscription_start
            )
            != pickup_location.id
        ):
            already_registered_member = None

        picking_mode = get_parameter_value(Parameter.PICKING_MODE, cache)

        if picking_mode == PICKING_MODE_SHARE:
            return PickupLocationCapacityModeShareChecker.check_for_picking_mode_share(
                pickup_location=pickup_location,
                ordered_products_to_quantity_map=ordered_products_to_quantity_map,
                already_registered_member=already_registered_member,
                subscription_start=subscription_start,
                global_cache=cache,
                pickup_location_cache=get_from_cache_or_compute(
                    cache, pickup_location, lambda: {}
                ),
            )
        elif picking_mode == PICKING_MODE_BASKET:
            return (
                PickupLocationCapacityModeBasketChecker.check_for_picking_mode_basket(
                    pickup_location=pickup_location,
                    ordered_products_to_quantity_map=ordered_products_to_quantity_map,
                    already_registered_member=already_registered_member,
                    subscription_start=subscription_start,
                    cache=cache,
                )
            )
        else:
            raise ImproperlyConfigured(f"Unknown picking mode: '{picking_mode}'")
