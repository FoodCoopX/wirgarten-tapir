import datetime

from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.models import GrowingPeriod, ProductType
from tapir.wirgarten.service.products import get_product_price


class ProductTypeLowestFreeCapacityAfterDateCalculator:
    @classmethod
    def get_lowest_free_capacity_after_date(
        cls,
        product_type: ProductType,
        reference_date: datetime.date,
        cache: dict,
    ):
        current_date = get_monday(reference_date)

        lowest_free_capacity = float("inf")
        last_date = cls.get_date_of_last_possible_capacity_change()
        while current_date < last_date:
            lowest_free_capacity = min(
                lowest_free_capacity,
                cls.get_free_capacity_at_date(
                    product_type=product_type,
                    reference_date=reference_date,
                    cache=cache,
                ),
            )
            current_date += datetime.timedelta(weeks=1)

        return float(lowest_free_capacity)

    @classmethod
    def get_free_capacity_at_date(
        cls,
        product_type: ProductType,
        reference_date: datetime.date,
        cache: dict,
    ):
        capacity_object = TapirCache.get_product_type_capacity_at_date(
            cache=cache, product_type=product_type, reference_date=reference_date
        )
        total_capacity = 0
        if capacity_object is not None:
            total_capacity = capacity_object.capacity

        capacity_usage = cls.get_capacity_usage_at_date(
            product_type=product_type, reference_date=reference_date, cache=cache
        )

        return total_capacity - capacity_usage

    @classmethod
    def get_capacity_usage_at_date(
        cls, product_type: ProductType, reference_date: datetime.date, cache: dict
    ):
        subscriptions_of_product_type = TapirCache.get_subscriptions_by_product_type(
            cache=cache
        ).get(product_type, set())
        relevant_subscriptions = (
            AutomaticSubscriptionRenewalService.get_subscriptions_and_renewals(
                reference_date=reference_date,
                subscription_filter=lambda subscription: subscription
                in subscriptions_of_product_type,
                cache=cache,
            )
        )

        usage = 0
        for subscription in relevant_subscriptions:
            usage += (
                get_product_price(
                    subscription.product_id, reference_date=reference_date, cache=cache
                ).size
                * subscription.quantity
            )
        return usage

    @classmethod
    def get_date_of_last_possible_capacity_change(cls):
        return GrowingPeriod.objects.order_by("-end_date").first().end_date
