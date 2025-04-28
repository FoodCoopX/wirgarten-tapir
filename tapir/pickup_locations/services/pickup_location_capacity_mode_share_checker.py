import datetime
from typing import Dict

from tapir.pickup_locations.services.highest_usage_after_date_service import (
    HighestUsageAfterDateService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.pickup_locations.services.share_capacities_service import (
    SharesCapacityService,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    Product,
    ProductType,
    Subscription,
)
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_product_price,
)


class PickupLocationCapacityModeShareChecker:
    @classmethod
    def check_for_picking_mode_share(
        cls,
        pickup_location: PickupLocation,
        ordered_products_to_quantity_map: Dict[Product, int],
        already_registered_member: Member | None,
        subscription_start: datetime.date,
        cache: Dict,
    ) -> bool:
        product_type_to_available_capacity_map = SharesCapacityService.get_available_share_capacities_for_pickup_location_by_product_type(
            pickup_location=pickup_location, cache=cache
        )

        for (
            product_type,
            available_capacity,
        ) in product_type_to_available_capacity_map.items():
            if available_capacity is None:
                # if the capacity in None, the location has unlimited capacity
                continue

            if not cls.check_capacity_for_product_type(
                product_type=product_type,
                member=already_registered_member,
                pickup_location=pickup_location,
                subscription_start=subscription_start,
                ordered_product_to_quantity_map=ordered_products_to_quantity_map,
                cache=cache,
            ):
                return False

        return True

    @classmethod
    def check_capacity_for_product_type(
        cls,
        product_type: ProductType,
        member: Member | None,
        pickup_location: PickupLocation,
        subscription_start: datetime.date,
        ordered_product_to_quantity_map: Dict[Product, int],
        cache: Dict,
    ):
        free_capacity = cls.get_free_capacity_at_date(
            product_type=product_type,
            pickup_location=pickup_location,
            reference_date=subscription_start,
            cache=cache,
        )

        amount_used_by_member_before_changes = (
            cls.get_capacity_used_by_member_before_changes(
                member=member,
                subscription_start=subscription_start,
                product_type=product_type,
                cache=cache,
            )
        )
        capacity_used_by_the_order = (
            cls.calculate_capacity_used_by_the_ordered_products(
                ordered_product_to_quantity_map=ordered_product_to_quantity_map,
                product_type=product_type,
                reference_date=subscription_start,
                cache=cache,
            )
        )

        return (
            free_capacity
            + amount_used_by_member_before_changes
            - capacity_used_by_the_order
            >= 0
        )

    @classmethod
    def get_capacity_usage_at_date(
        cls,
        pickup_location: PickupLocation,
        product_type: ProductType,
        reference_date: datetime.date,
        cache: Dict,
    ):
        member_ids_at_pickup_location = (
            MemberPickupLocationService.get_members_ids_at_pickup_location(
                pickup_location,
                reference_date,
                cache,
            )
        )

        subscriptions_with_product_type = TapirCache.get_subscriptions_by_product_type(
            cache
        )[product_type]

        def subscription_filter(subscription: Subscription):
            return (
                subscription in subscriptions_with_product_type
                and subscription.member_id in member_ids_at_pickup_location
            )

        relevant_subscriptions = (
            AutomaticSubscriptionRenewalService.get_subscriptions_and_renewals(
                reference_date=reference_date,
                subscription_filter=subscription_filter,
                cache=cache,
            )
        )

        total_size = 0
        for subscription in relevant_subscriptions:
            size = get_product_price(
                subscription.product_id, reference_date, cache
            ).size
            total_size += size * subscription.quantity

        return float(total_size)

    @classmethod
    def get_capacity_used_by_member_before_changes(
        cls,
        member: Member | None,
        subscription_start: datetime.date,
        product_type: ProductType,
        cache: Dict,
    ):
        if member is None:
            return 0

        return float(
            sum(
                [
                    s.get_used_capacity(cache=cache)
                    for s in get_active_subscriptions(
                        subscription_start, cache=cache
                    ).filter(
                        member_id=member.id,
                        product__type_id=product_type.id,
                    )
                ]
            )
        )

    @staticmethod
    def calculate_capacity_used_by_the_ordered_products(
        ordered_product_to_quantity_map: Dict[Product, int],
        product_type: ProductType,
        reference_date: datetime.date,
        cache: Dict,
    ):
        total = 0.0
        for ordered_product, quantity in ordered_product_to_quantity_map.items():
            if ordered_product.type != product_type:
                continue
            total += (
                float(get_product_price(ordered_product, reference_date, cache).size)
                * quantity
            )
        return total

    @classmethod
    def get_highest_usage_after_date(
        cls,
        pickup_location: PickupLocation,
        product_type: ProductType,
        reference_date: datetime.date,
        cache: Dict,
    ):
        return HighestUsageAfterDateService.get_highest_usage_after_date_generic(
            pickup_location=pickup_location,
            reference_date=reference_date,
            lambda_get_usage_at_date=lambda data: (
                PickupLocationCapacityModeShareChecker.get_capacity_usage_at_date(
                    pickup_location=pickup_location,
                    product_type=product_type,
                    reference_date=data,
                    cache=cache,
                )
            ),
            cache=cache,
        )

    @classmethod
    def get_free_capacity_at_date(
        cls,
        product_type: ProductType,
        pickup_location: PickupLocation,
        reference_date: datetime.date,
        cache: Dict,
    ):
        product_type_to_available_capacity_map = SharesCapacityService.get_available_share_capacities_for_pickup_location_by_product_type(
            pickup_location=pickup_location, cache=cache
        )

        available_capacity = product_type_to_available_capacity_map.get(product_type, 0)

        usage = cls.get_highest_usage_after_date(
            pickup_location=pickup_location,
            product_type=product_type,
            reference_date=reference_date,
            cache=cache,
        )
        free_capacity = available_capacity - usage

        return free_capacity
