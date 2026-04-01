import datetime

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
        product_wishes = WaitingListProductWish.objects.filter(
            product__type_id=product_type_id
        ).select_related("product")

        if pickup_location is not None:
            relevant_entries = WaitingListEntry.objects.filter(
                pickup_location_wishes__pickup_location=pickup_location
            )
            product_wishes = product_wishes.filter(
                waiting_list_entry__in=relevant_entries
            )

        reserved_capacity = 0
        for product_wish in product_wishes:
            product_size = get_product_price(
                product=product_wish.product, reference_date=reference_date, cache=cache
            ).size
            reserved_capacity += product_size * product_wish.quantity

        return reserved_capacity
