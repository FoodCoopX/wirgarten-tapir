import datetime
from typing import Dict, Callable

from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_from_cache_or_compute, get_monday
from tapir.wirgarten.models import (
    PickupLocation,
    MemberPickupLocation,
)


class PickupLocationHighestUsageAfterDateService:
    @classmethod
    def get_highest_usage_after_date_generic(
        cls,
        pickup_location: PickupLocation,
        reference_date: datetime.date,
        lambda_get_usage_at_date: Callable,
        cache: Dict,
    ):
        current_date = reference_date
        max_usage = 0

        date_of_last_possible_capacity_change = (
            cls.get_date_of_last_possible_capacity_change(
                cache=cache, pickup_location=pickup_location
            )
        )

        while current_date < date_of_last_possible_capacity_change:
            usage_at_date = lambda_get_usage_at_date(current_date)
            max_usage = max(max_usage, usage_at_date)
            current_date = get_monday(current_date + datetime.timedelta(days=7))

        return max_usage

    @staticmethod
    def get_date_of_last_possible_capacity_change(
        pickup_location: PickupLocation,
        cache: Dict,
    ):
        def compute():
            last_pickup_location_change = (
                MemberPickupLocation.objects.filter(pickup_location=pickup_location)
                .order_by("valid_from")
                .last()
            )
            last_subscription = TapirCache.get_last_subscription(cache=cache)
            if not last_pickup_location_change:
                return last_subscription.end_date
            if not last_subscription:
                return last_pickup_location_change.valid_from
            return max(
                last_pickup_location_change.valid_from,
                last_subscription.end_date,
            )

        pickup_location_cache = get_from_cache_or_compute(
            cache, pickup_location, lambda: {}
        )
        return get_from_cache_or_compute(
            pickup_location_cache, "date_of_last_possible_capacity_change", compute
        )
