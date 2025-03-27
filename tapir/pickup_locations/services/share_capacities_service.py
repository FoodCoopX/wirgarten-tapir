from icecream import ic

from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import PickupLocation, ProductType, PickupLocationCapability


class SharesCapacityService:
    @classmethod
    def get_available_share_capacities_for_pickup_location_by_product_type(
        cls, pickup_location: PickupLocation
    ):
        capacities = {
            product_type: None
            for product_type in ProductType.objects.exclude(
                delivery_cycle=NO_DELIVERY[0]
            )
        }
        ic(pickup_location)
        for capability in PickupLocationCapability.objects.filter(
            pickup_location=pickup_location
        ):
            if capability.product_type not in capacities.keys():
                continue

            capacities[capability.product_type] = capability.max_capacity
        return capacities
