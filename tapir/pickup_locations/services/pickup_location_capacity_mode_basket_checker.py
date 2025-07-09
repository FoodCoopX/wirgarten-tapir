import datetime
from typing import Dict

from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.pickup_locations.services.highest_usage_after_date_service import (
    HighestUsageAfterDateService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    Product,
    Subscription,
    MemberPickupLocation,
)
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
)


class PickupLocationCapacityModeBasketChecker:
    @classmethod
    def check_for_picking_mode_basket(
        cls,
        pickup_location: PickupLocation,
        ordered_products_to_quantity_map: Dict[Product, int],
        already_registered_member: Member | None,
        subscription_start: datetime.date,
        cache: Dict,
    ) -> bool:
        basket_size_to_available_capacity_map = (
            cls.get_basket_size_to_available_capacity_map(cache, pickup_location)
        )

        for (
            basket_size,
            available_capacity,
        ) in basket_size_to_available_capacity_map.items():
            if available_capacity is None:
                # if the capacity in None, the location has unlimited capacity
                continue

            if not cls.check_capacity_for_basket_size(
                basket_size=basket_size,
                member=already_registered_member,
                pickup_location=pickup_location,
                subscription_start=subscription_start,
                ordered_product_to_quantity_map=ordered_products_to_quantity_map,
                cache=cache,
            ):
                return False

        return True

    @classmethod
    def check_capacity_for_basket_size(
        cls,
        basket_size: str,
        member: Member | None,
        pickup_location: PickupLocation,
        subscription_start: datetime.date,
        ordered_product_to_quantity_map: Dict[Product, int],
        cache: Dict,
    ):
        capacity_used_by_the_order = (
            cls.calculate_capacity_used_by_the_ordered_products(
                ordered_product_to_quantity_map=ordered_product_to_quantity_map,
                basket_size=basket_size,
                cache=cache,
            )
        )
        if capacity_used_by_the_order == 0:
            return True

        free_capacity = cls.get_free_capacity_at_date(
            pickup_location=pickup_location,
            basket_size=basket_size,
            reference_date=subscription_start,
            cache=cache,
        )
        amount_used_by_member_before_changes = (
            cls.get_capacity_used_by_member_before_changes(
                member=member,
                subscription_start=subscription_start,
                basket_size=basket_size,
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
    def calculate_capacity_usage_at_date(
        cls,
        pickup_location: PickupLocation,
        basket_size: str,
        reference_date: datetime.date,
        cache: Dict,
    ):
        member_ids_at_pickup_location = (
            MemberPickupLocationService.get_members_ids_at_pickup_location(
                pickup_location, reference_date, cache
            )
        )

        def subscription_filter(subscription: Subscription):
            return subscription.member_id in member_ids_at_pickup_location

        relevant_subscriptions = (
            AutomaticSubscriptionRenewalService.get_subscriptions_and_renewals(
                reference_date=reference_date,
                subscription_filter=subscription_filter,
                cache=cache,
            )
        )

        total_usage = 0
        for subscription in relevant_subscriptions:
            total_usage += (
                cls.get_basket_size_usage(cache, subscription.product_id, basket_size)
                * subscription.quantity
            )

        return total_usage

    @classmethod
    def get_capacity_usage_at_date(
        cls,
        pickup_location: PickupLocation,
        basket_size: str,
        reference_date: datetime.date,
        cache: Dict,
    ):
        pickup_location_cache = get_from_cache_or_compute(
            cache, pickup_location, lambda: {}
        )
        capacity_usage_by_basket_size = get_from_cache_or_compute(
            pickup_location_cache, "capacity_usage_by_basket_size", lambda: {}
        )
        capacity_usage_by_date = get_from_cache_or_compute(
            capacity_usage_by_basket_size, basket_size, lambda: {}
        )
        return get_from_cache_or_compute(
            capacity_usage_by_date,
            reference_date,
            lambda: cls.calculate_capacity_usage_at_date(
                pickup_location=pickup_location,
                basket_size=basket_size,
                reference_date=reference_date,
                cache=cache,
            ),
        )

    @classmethod
    def get_capacity_used_by_member_before_changes(
        cls,
        member: Member | None,
        subscription_start: datetime.date,
        basket_size: str,
        cache: Dict,
    ):
        if member is None:
            return 0

        usage = 0
        for subscription in get_active_subscriptions(subscription_start).filter(
            member=member
        ):
            usage += (
                cls.get_basket_size_usage(cache, subscription.product_id, basket_size)
                * subscription.quantity
            )

        return usage

    @classmethod
    def calculate_capacity_used_by_the_ordered_products(
        cls,
        ordered_product_to_quantity_map: Dict[Product, int],
        basket_size: str,
        cache: Dict,
    ):
        total = 0.0
        for ordered_product, quantity in ordered_product_to_quantity_map.items():
            total += (
                cls.get_basket_size_usage(cache, ordered_product.id, basket_size)
                * quantity
            )
        return total

    @classmethod
    def get_highest_usage_after_date(
        cls,
        pickup_location: PickupLocation,
        basket_size: str,
        reference_date: datetime.date,
        cache: Dict,
    ):
        return HighestUsageAfterDateService.get_highest_usage_after_date_generic(
            pickup_location=pickup_location,
            reference_date=reference_date,
            lambda_get_usage_at_date=lambda date: PickupLocationCapacityModeBasketChecker.get_capacity_usage_at_date(
                pickup_location=pickup_location,
                basket_size=basket_size,
                reference_date=date,
                cache=cache,
            ),
            cache=cache,
        )

    @classmethod
    def get_free_capacity_at_date(
        cls,
        pickup_location: PickupLocation,
        basket_size: str,
        reference_date: datetime.date,
        cache: Dict,
    ):
        basket_size_to_available_capacity_map = (
            cls.get_basket_size_to_available_capacity_map(
                cache=cache, pickup_location=pickup_location
            )
        )
        capacity = basket_size_to_available_capacity_map[basket_size]

        usage = cls.get_highest_usage_after_date(
            pickup_location=pickup_location,
            basket_size=basket_size,
            reference_date=reference_date,
            cache=cache,
        )

        return capacity - usage

    @classmethod
    def get_basket_size_to_available_capacity_map(
        cls, cache: Dict, pickup_location: PickupLocation
    ):
        pickup_location_cache = get_from_cache_or_compute(
            cache, pickup_location, lambda: {}
        )
        return get_from_cache_or_compute(
            pickup_location_cache,
            "basket_size_to_available_capacity_map",
            lambda: BasketSizeCapacitiesService.get_basket_size_capacities_for_pickup_location(
                pickup_location, cache=cache
            ),
        )

    @classmethod
    def get_member_pickup_locations(cls, cache: Dict):
        def build_if_cache_miss():
            member_pickup_locations = {}
            for member_pickup_location in MemberPickupLocation.objects.order_by(
                "valid_from"
            ):
                if member_pickup_location.member_id not in member_pickup_locations:
                    member_pickup_locations[member_pickup_location.member_id] = []
                member_pickup_locations[member_pickup_location.member_id].append(
                    member_pickup_location
                )

        return get_from_cache_or_compute(
            cache, "member_pickup_locations", build_if_cache_miss
        )

    @classmethod
    def build_product_to_basket_size_to_usage_map(
        cls, cache: Dict
    ) -> Dict[str, Dict[str, int]]:
        def compute():
            basket_sizes = BasketSizeCapacitiesService.get_basket_sizes(cache=cache)
            product_id_to_basket_size_to_usage_map = {}
            for product_id in Product.objects.values_list("id", flat=True):
                product_id_to_basket_size_to_usage_map[product_id] = {}
                for basket_size in basket_sizes:
                    basket_size_usage = 0

                    equivalence = ProductBasketSizeEquivalence.objects.filter(
                        basket_size_name=basket_size, product_id=product_id
                    ).first()
                    if equivalence:
                        basket_size_usage = equivalence.quantity

                    product_id_to_basket_size_to_usage_map[product_id][
                        basket_size
                    ] = basket_size_usage
            return product_id_to_basket_size_to_usage_map

        return get_from_cache_or_compute(
            cache, "product_to_basket_size_to_usage_map", compute
        )

    @classmethod
    def get_basket_size_usage(cls, cache: Dict, product_id: str, basket_size: str):
        def compute():
            return cls.build_product_to_basket_size_to_usage_map(cache=cache)

        product_to_basket_size_to_usage_map = get_from_cache_or_compute(
            cache, "product_to_basket_size_to_usage_map", compute
        )
        return product_to_basket_size_to_usage_map[product_id][basket_size]
