import datetime

from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import (
    PickupLocation,
    WaitingListProductWish,
    WaitingListEntry,
)
from tapir.wirgarten.service.products import get_product_price


class WaitingListReservedCapacityCalculator:
    @classmethod
    def calculate_capacity_reserved_by_the_waiting_list_entries(
        cls,
        product_type_id,
        pickup_location: PickupLocation | None,
        reference_date: datetime.date,
        cache: dict,
    ):
        reserved_capacities_by_product_type_and_pickup_location = (
            get_from_cache_or_compute(
                cache,
                "waiting_list_reserved_capacities_by_product_type_and_pickup_location",
                lambda: cls._compute_all_reserved_capacities(reference_date, cache),
            )
        )

        pickup_location_key = pickup_location.id if pickup_location else "__global__"
        return reserved_capacities_by_product_type_and_pickup_location.get(
            (product_type_id, pickup_location_key), 0
        )

    @classmethod
    def _compute_all_reserved_capacities(
        cls, reference_date: datetime.date, cache: dict
    ):

        all_product_wishes = list(
            WaitingListProductWish.objects.select_related(
                "product", "product__type", "waiting_list_entry"
            ).prefetch_related("waiting_list_entry__pickup_location_wishes")
        )

        result = {}
        for wish in all_product_wishes:
            product = wish.product
            product_type_id = product.type_id
            product_size = get_product_price(
                product=product, reference_date=reference_date, cache=cache
            ).size
            capacity = product_size * wish.quantity

            result[(product_type_id, "__global__")] = (
                result.get((product_type_id, "__global__"), 0) + capacity
            )

            entry = wish.waiting_list_entry
            for pickup_location_wish in entry.pickup_location_wishes.all():
                key = (product_type_id, pickup_location_wish.pickup_location_id)
                result[key] = result.get(key, 0) + capacity

        return result
