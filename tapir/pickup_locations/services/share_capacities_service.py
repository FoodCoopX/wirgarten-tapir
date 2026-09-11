from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import PickupLocation, PickupLocationCapability


class SharesCapacityService:
    @classmethod
    def get_available_share_capacities_for_pickup_location_by_product_type(
        cls, pickup_location: PickupLocation, cache: dict
    ):
        def compute():
            product_types = [
                product_type
                for product_type in TapirCache.get_all_product_types(cache=cache)
                if product_type.delivery_cycle != NO_DELIVERY[0]
            ]
            capacities = dict.fromkeys(product_types, None)
            for capability in PickupLocationCapability.objects.filter(
                pickup_location=pickup_location
            ).select_related("product_type"):
                if capability.product_type not in capacities:
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
