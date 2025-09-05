import datetime

from tapir.subscriptions.services.product_type_lowest_free_capacity_after_date_generic import (
    ProductTypeLowestFreeCapacityAfterDateCalculator,
)
from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.waiting_list.services.waiting_list_reserved_capacity_calculator import (
    WaitingListReservedCapacityCalculator,
)
from tapir.wirgarten.service.products import (
    get_product_price,
)


class GlobalCapacityChecker:
    @classmethod
    def get_product_type_ids_without_enough_capacity_for_order(
        cls,
        order_with_all_product_types: TapirOrder,
        member_id: str | None,
        subscription_start_date: datetime.date,
        cache: dict,
    ):
        product_type_ids = {
            product.type_id for product in order_with_all_product_types.keys()
        }
        product_type_ids_without_enough_capacity = []
        for product_type_id in product_type_ids:
            enough = cls.is_there_enough_free_global_capacity_for_single_product_type(
                order_for_a_single_product_type={
                    product: quantity
                    for product, quantity in order_with_all_product_types.items()
                    if product.type_id == product_type_id
                },
                member_id=member_id,
                subscription_start_date=subscription_start_date,
                product_type_id=product_type_id,
                check_waiting_list_entries=True,
                cache=cache,
            )
            if not enough:
                product_type_ids_without_enough_capacity.append(product_type_id)

        return product_type_ids_without_enough_capacity

    @classmethod
    def calculate_global_capacity_used_by_the_ordered_products(
        cls,
        order_for_a_single_product_type: TapirOrder,
        reference_date: datetime.date,
        cache: dict = None,
    ):
        total = 0.0
        for product, quantity in order_for_a_single_product_type.items():
            product_price_object = get_product_price(
                product=product, reference_date=reference_date, cache=cache
            )
            total += float(product_price_object.size) * quantity
        return total

    @classmethod
    def is_there_enough_free_global_capacity_for_single_product_type(
        cls,
        order_for_a_single_product_type: TapirOrder,
        member_id: str | None,
        subscription_start_date: datetime.date,
        product_type_id,
        check_waiting_list_entries: bool,
        cache: dict,
    ):
        free_capacity = ProductTypeLowestFreeCapacityAfterDateCalculator.get_lowest_free_capacity_after_date(
            product_type=TapirCache.get_product_type_by_id(
                product_type_id=product_type_id, cache=cache
            ),
            reference_date=subscription_start_date,
            cache=cache,
        )

        capacity_used_by_the_ordered_products = (
            cls.calculate_global_capacity_used_by_the_ordered_products(
                order_for_a_single_product_type=order_for_a_single_product_type,
                reference_date=subscription_start_date,
                cache=cache,
            )
        )

        capacity_used_by_the_current_subscriptions = SubscriptionChangeValidator.calculate_capacity_used_by_the_current_subscriptions(
            product_type_id=product_type_id,
            member_id=member_id,
            subscription_start_date=subscription_start_date,
            cache=cache,
        )

        capacity_reserved_by_the_waiting_list_entries = 0
        if check_waiting_list_entries:
            capacity_reserved_by_the_waiting_list_entries = WaitingListReservedCapacityCalculator.calculate_capacity_reserved_by_the_waiting_list_entries(
                product_type=TapirCache.get_product_type_by_id(
                    cache=cache, product_type_id=product_type_id
                ),
                pickup_location=None,
                reference_date=subscription_start_date,
                cache=cache,
            )

        return free_capacity >= (
            capacity_used_by_the_ordered_products
            - float(capacity_used_by_the_current_subscriptions)
            + float(capacity_reserved_by_the_waiting_list_entries)
        )
