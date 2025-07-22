import datetime

from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.product_type_lowest_free_capacity_after_date_generic import (
    ProductTypeLowestFreeCapacityAfterDateCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.models import Product
from tapir.wirgarten.service.products import get_active_subscriptions


class ProductCapacityChecker:
    @classmethod
    def does_product_have_enough_free_capacity_to_add_order(
        cls,
        product: Product,
        ordered_quantity: int,
        member_id: str | None,
        subscription_start_date: datetime.date,
        cache: dict,
    ):
        if product.capacity is None:
            return True

        total_capacity = product.capacity

        used_capacity = cls.get_highest_capacity_usage_after_date(
            product=product, reference_date=subscription_start_date, cache=cache
        )

        capacity_used_by_the_ordered_products = ordered_quantity

        capacity_used_by_the_current_subscriptions = 0
        if member_id is not None:
            subscription = (
                get_active_subscriptions(
                    reference_date=subscription_start_date, cache=cache
                )
                .filter(member_id=member_id)
                .first()
            )
            if subscription is not None:
                capacity_used_by_the_current_subscriptions = subscription.quantity

        return (
            total_capacity
            - used_capacity
            - capacity_used_by_the_ordered_products
            + capacity_used_by_the_current_subscriptions
            > 0
        )

    @classmethod
    def get_highest_capacity_usage_after_date(
        cls, product: Product, reference_date: datetime.date, cache: dict
    ):
        current_date = get_monday(reference_date)

        highest_usage = float("-inf")
        while (
            current_date
            < ProductTypeLowestFreeCapacityAfterDateCalculator.get_date_of_last_possible_capacity_change()
        ):
            highest_usage = max(
                highest_usage,
                cls.get_capacity_usage_at_date(
                    product=product,
                    reference_date=reference_date,
                    cache=cache,
                ),
            )
            current_date += datetime.timedelta(weeks=1)

        return highest_usage

    @classmethod
    def get_capacity_usage_at_date(
        cls, product: Product, reference_date: datetime.date, cache: dict
    ):
        subscriptions_of_product = {
            subscription
            for subscription in TapirCache.get_all_subscriptions(cache=cache)
            if subscription.product_id == product.id
        }
        relevant_subscriptions = (
            AutomaticSubscriptionRenewalService.get_subscriptions_and_renewals(
                reference_date=reference_date,
                subscription_filter=lambda subscription: subscription
                in subscriptions_of_product,
                cache=cache,
            )
        )

        return sum([subscription.quantity for subscription in relevant_subscriptions])
