import datetime
from typing import Dict

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    Product,
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
        global_cache: Dict,
        pickup_location_cache: Dict,
    ) -> bool:
        basket_size_to_available_capacity_map = get_from_cache_or_compute(
            pickup_location_cache,
            "basket_size_to_available_capacity_map",
            lambda: BasketSizeCapacitiesService.get_basket_size_capacities_for_pickup_location(
                pickup_location
            ),
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
                global_cache=global_cache,
                pickup_location_cache=pickup_location_cache,
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
        global_cache: Dict,
        pickup_location_cache: Dict,
    ):
        free_capacity = cls.get_free_capacity_at_date(
            pickup_location=pickup_location,
            basket_size=basket_size,
            reference_date=subscription_start,
            global_cache=global_cache,
            pickup_location_cache=pickup_location_cache,
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
                global_cache=global_cache,
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
        global_cache: Dict,
    ):
        map_cache = get_from_cache_or_compute(
            global_cache, "product_id_to_basket_size_usage_map", lambda: {}
        )

        product_id_to_basket_size_usage_map = get_from_cache_or_compute(
            map_cache,
            basket_size,
            lambda: cls.get_product_id_to_basket_size_usage_map(basket_size),
        )

        members_at_pickup_location = []
        for member, mpls in global_cache["member_pickup_locations"].items():
            current_mpl = None
            for mpl in mpls:
                if mpl.valid_from <= reference_date and (
                    current_mpl is None or current_mpl.valid_from < mpl.valid_from
                ):
                    current_mpl = mpl
            if current_mpl and current_mpl.pickup_location_id == pickup_location.id:
                members_at_pickup_location.append(member)

        subscriptions_active_at_reference_date = {
            subscription
            for subscription in global_cache["active_and_future_subscriptions"]
            if (
                subscription.start_date <= reference_date <= subscription.end_date
                and subscription.member in members_at_pickup_location
            )
        }

        relevant_subscriptions = subscriptions_active_at_reference_date
        if get_parameter_value(
            Parameter.SUBSCRIPTION_AUTOMATIC_RENEWAL,
            get_from_cache_or_compute(global_cache, "parameter_cache", lambda: {}),
        ):
            relevant_subscriptions = cls.extend_subscriptions_with_those_that_will_be_renewed(
                subscriptions_active_at_reference_date=subscriptions_active_at_reference_date,
                reference_date=reference_date,
                members_at_pickup_location=members_at_pickup_location,
                global_cache=global_cache,
            )

        total_usage = 0
        for subscription in relevant_subscriptions:
            total_usage += (
                product_id_to_basket_size_usage_map[subscription.product_id]
                * subscription.quantity
            )

        return total_usage

    @classmethod
    def extend_subscriptions_with_those_that_will_be_renewed(
        cls,
        subscriptions_active_at_reference_date,
        reference_date: datetime.date,
        members_at_pickup_location,
        global_cache: Dict,
    ):
        relevant_subscriptions = subscriptions_active_at_reference_date

        current_growing_period = get_current_growing_period(
            reference_date,
            get_from_cache_or_compute(
                global_cache, "growing_period_at_date", lambda: {}
            ),
        )

        members_that_have_a_subscription_of_product_at_reference_date = {
            subscription.member for subscription in relevant_subscriptions
        }

        end_of_previous_growing_period = (
            current_growing_period.start_date - datetime.timedelta(days=1)
        )
        subscriptions_that_will_get_renewed = {
            subscription
            for subscription in global_cache["active_and_future_subscriptions"]
            if (
                subscription.start_date
                <= end_of_previous_growing_period
                <= subscription.end_date
                and subscription.member in members_at_pickup_location
                and subscription.cancellation_ts is None
                and subscription.member
                not in members_that_have_a_subscription_of_product_at_reference_date
            )
        }

        relevant_subscriptions.update(subscriptions_that_will_get_renewed)

        return relevant_subscriptions

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
        global_cache: Dict,
    ):
        map_cache = get_from_cache_or_compute(
            global_cache, "product_id_to_basket_size_usage_map", lambda: {}
        )
        product_id_to_basket_size_usage_map = get_from_cache_or_compute(
            map_cache,
            basket_size,
            lambda: cls.get_product_id_to_basket_size_usage_map(basket_size),
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
        global_cache: Dict,
        pickup_location_cache: Dict,
    ):
        return PickupLocationCapacityModeShareChecker.get_highest_usage_after_date_generic(
            pickup_location=pickup_location,
            reference_date=reference_date,
            lambda_get_usage_at_date=lambda date: PickupLocationCapacityModeBasketChecker.get_capacity_usage_at_date(
                pickup_location=pickup_location,
                basket_size=basket_size,
                reference_date=date,
                global_cache=global_cache,
            ),
            global_cache=global_cache,
            pickup_location_cache=pickup_location_cache,
        )

    @classmethod
    def get_free_capacity_at_date(
        cls,
        pickup_location: PickupLocation,
        basket_size: str,
        reference_date: datetime.date,
        global_cache: Dict,
        pickup_location_cache: Dict,
    ):
        basket_size_to_available_capacity_map = get_from_cache_or_compute(
            pickup_location_cache,
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
            global_cache=global_cache,
            pickup_location_cache=pickup_location_cache,
        )

        return capacity - usage
