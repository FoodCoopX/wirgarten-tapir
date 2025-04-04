import datetime
from typing import Dict

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    Product,
    Subscription,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_current_growing_period,
)


class PickupLocationCapacityModeBasketChecker:
    @classmethod
    def check_for_picking_mode_basket(
        cls,
        pickup_location: PickupLocation,
        ordered_product_to_quantity_map: Dict[Product, int],
        already_registered_member: Member | None,
        subscription_start: datetime.date,
    ) -> bool:
        basket_size_to_available_capacity_map = (
            BasketSizeCapacitiesService.get_basket_size_capacities_for_pickup_location(
                pickup_location
            )
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
                ordered_product_to_quantity_map=ordered_product_to_quantity_map,
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
    ):
        free_capacity = cls.get_free_capacity_at_date(
            pickup_location=pickup_location,
            basket_size=basket_size,
            reference_date=subscription_start,
            cache={},
        )
        amount_used_by_member_before_changes = (
            cls.get_capacity_used_by_member_before_changes(
                member=member,
                subscription_start=subscription_start,
                basket_size=basket_size,
            )
        )
        capacity_used_by_the_order = (
            cls.calculate_capacity_used_by_the_ordered_products(
                ordered_product_to_quantity_map=ordered_product_to_quantity_map,
                basket_size=basket_size,
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
        basket_size: str,
        reference_date: datetime.date,
        cache: Dict,
    ):
        product_id_to_basket_size_usage_map = get_from_cache_or_compute(
            cache,
            "product_id_to_basket_size_usage_map",
            lambda: cls.get_product_id_to_basket_size_usage_map(basket_size),
        )

        members_at_pickup_location = (
            MemberPickupLocationService.get_members_at_pickup_location(
                pickup_location, reference_date
            )
        )

        subscriptions_active_at_reference_date = get_active_subscriptions(
            reference_date,
            get_from_cache_or_compute(cache, "parameter_cache", lambda: None),
        ).filter(member__in=members_at_pickup_location)

        relevant_subscriptions = subscriptions_active_at_reference_date
        if get_parameter_value(
            Parameter.SUBSCRIPTION_AUTOMATIC_RENEWAL,
            get_from_cache_or_compute(cache, "parameter_cache", lambda: None),
        ):
            relevant_subscriptions = cls.extend_subscriptions_with_those_that_will_be_renewed(
                subscriptions_active_at_reference_date=subscriptions_active_at_reference_date,
                reference_date=reference_date,
                members_at_pickup_location=members_at_pickup_location,
                cache=cache,
            )

        total_usage = 0
        for subscription in relevant_subscriptions:
            total_usage += (
                product_id_to_basket_size_usage_map[subscription.product.id]
                * subscription.quantity
            )

        return total_usage

    @classmethod
    def extend_subscriptions_with_those_that_will_be_renewed(
        cls,
        subscriptions_active_at_reference_date,
        reference_date: datetime.date,
        members_at_pickup_location,
        cache: Dict | None = None,
    ):
        relevant_subscriptions = set(subscriptions_active_at_reference_date)

        current_growing_period = get_current_growing_period(
            reference_date,
            get_from_cache_or_compute(cache, "growing_period_at_date", lambda: {}),
        )

        members_that_have_a_subscription_of_product_at_reference_date = (
            subscriptions_active_at_reference_date.values_list("member", flat=True)
        )
        subscriptions_that_will_get_renewed = (
            get_active_subscriptions(
                current_growing_period.start_date - datetime.timedelta(days=1),
                get_from_cache_or_compute(cache, "parameter_cache", lambda: None),
            )
            .filter(
                member__in=members_at_pickup_location,
                cancellation_ts__isnull=True,
            )
            .exclude(
                member__in=members_that_have_a_subscription_of_product_at_reference_date
            )
        )
        relevant_subscriptions.update(subscriptions_that_will_get_renewed)

        return Subscription.objects.filter(
            id__in=[subscription.id for subscription in relevant_subscriptions]
        ).distinct()

    @classmethod
    def get_capacity_used_by_member_before_changes(
        cls,
        member: Member | None,
        subscription_start: datetime.date,
        basket_size: str,
    ):
        if member is None:
            return 0

        product_id_to_basket_size_usage_map = (
            cls.get_product_id_to_basket_size_usage_map(basket_size)
        )

        usage = 0
        for subscription in get_active_subscriptions(subscription_start).filter(
            member=member
        ):
            usage += (
                product_id_to_basket_size_usage_map[subscription.product_id]
                * subscription.quantity
            )

        return usage

    @classmethod
    def get_product_id_to_basket_size_usage_map(cls, basket_size: str):
        product_id_to_basket_size_usage_map = {}
        for product in Product.objects.all():
            product_id_to_basket_size_usage_map[product.id] = 0

            equivalence = ProductBasketSizeEquivalence.objects.filter(
                basket_size_name=basket_size, product=product
            ).first()
            if equivalence:
                product_id_to_basket_size_usage_map[product.id] = equivalence.quantity
        return product_id_to_basket_size_usage_map

    @classmethod
    def calculate_capacity_used_by_the_ordered_products(
        cls,
        ordered_product_to_quantity_map: Dict[Product, int],
        basket_size: str,
    ):
        product_id_to_basket_size_usage_map = (
            cls.get_product_id_to_basket_size_usage_map(basket_size)
        )
        total = 0.0
        for ordered_product, quantity in ordered_product_to_quantity_map.items():
            total += product_id_to_basket_size_usage_map[ordered_product.id] * quantity
        return total

    @classmethod
    def get_highest_usage_after_date(
        cls,
        pickup_location: PickupLocation,
        basket_size: str,
        reference_date: datetime.date,
        cache: Dict,
    ):
        return (
            PickupLocationCapacityModeShareChecker.get_highest_usage_after_date_generic(
                pickup_location=pickup_location,
                reference_date=reference_date,
                lambda_get_usage_at_date=lambda date: (
                    PickupLocationCapacityModeBasketChecker.get_capacity_usage_at_date(
                        pickup_location=pickup_location,
                        basket_size=basket_size,
                        reference_date=date,
                        cache=cache,
                    )
                ),
                cache=cache,
            )
        )

    @classmethod
    def get_free_capacity_at_date(
        cls,
        pickup_location: PickupLocation,
        basket_size: str,
        reference_date: datetime.date,
        cache: Dict | None = None,
    ):
        basket_size_to_available_capacity_map = get_from_cache_or_compute(
            cache,
            "basket_size_to_available_capacity_map",
            lambda: BasketSizeCapacitiesService.get_basket_size_capacities_for_pickup_location(
                pickup_location
            ),
        )
        capacity = basket_size_to_available_capacity_map[basket_size]

        usage = cls.get_highest_usage_after_date(
            pickup_location=pickup_location,
            basket_size=basket_size,
            reference_date=reference_date,
            cache=cache,
        )

        return capacity - usage
