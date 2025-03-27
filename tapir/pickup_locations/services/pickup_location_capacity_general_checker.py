import datetime
from typing import Dict

from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.config import PICKING_MODE_SHARE, PICKING_MODE_BASKET
from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
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
    ) -> bool:
        picking_mode = get_parameter_value(Parameter.PICKING_MODE)
        if picking_mode is PICKING_MODE_SHARE:
            return PickupLocationCapacityModeShareChecker.check_for_picking_mode_share(
                pickup_location,
                ordered_products_to_quantity_map,
                already_registered_member,
                subscription_start,
            )
        elif picking_mode is PICKING_MODE_BASKET:
            return cls.check_for_picking_mode_basket(
                pickup_location,
                ordered_products_to_quantity_map,
                already_registered_member,
            )
        else:
            raise ImproperlyConfigured(f"Unknown picking mode: '{picking_mode}'")

    @classmethod
    def check_for_picking_mode_basket(
        cls,
        pickup_location: PickupLocation,
        product_to_quantity_map: Dict[Product, int],
        already_registered_member: Member | None,
    ) -> bool:
        raise NotImplementedError()
