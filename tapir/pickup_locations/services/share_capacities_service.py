from typing import Dict

from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import PickupLocation, ProductType, PickupLocationCapability


class SharesCapacityService:
    @classmethod
    def get_available_share_capacities_for_pickup_location_by_product_type(
        cls, pickup_location: PickupLocation, cache: Dict = None
    ):
        def compute():
            capacities = {
                product_type: None
                for product_type in ProductType.objects.exclude(
                    delivery_cycle=NO_DELIVERY[0]
                )
            }
            for capability in PickupLocationCapability.objects.filter(
                pickup_location=pickup_location
            ):
                if capability.product_type not in capacities.keys():
                    continue

                capacities[capability.product_type] = capability.max_capacity
            return capacities

        pickup_location_cache = get_from_cache_or_compute(
            cache, pickup_location, lambda: {}
        )
        return get_from_cache_or_compute(
            pickup_location_cache,
            "available_share_capacities_for_pickup_location_by_product_type",
            compute,
        )
