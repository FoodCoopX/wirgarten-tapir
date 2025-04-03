import datetime
from typing import Dict

from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    Product,
)
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_active_and_future_subscriptions,
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
                available_capacity=available_capacity,
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
        available_capacity: int,
        member: Member | None,
        pickup_location: PickupLocation,
        subscription_start: datetime.date,
        ordered_product_to_quantity_map: Dict[Product, int],
    ):
        current_usage = cls.get_current_capacity_usage(
            pickup_location=pickup_location,
            basket_size=basket_size,
            subscription_start=subscription_start,
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
        capacity_usage_after_changes = (
            current_usage
            - amount_used_by_member_before_changes
            + capacity_used_by_the_order
        )
        return capacity_usage_after_changes <= available_capacity

    @classmethod
    def get_current_capacity_usage(
        cls,
        pickup_location: PickupLocation,
        basket_size: str,
        subscription_start: datetime.date,
    ):
        product_id_to_basket_size_usage_map = (
            cls.get_product_id_to_basket_size_usage_map(basket_size)
        )

        members_at_pickup_location = (
            MemberPickupLocationService.get_members_at_pickup_location(
                pickup_location, subscription_start
            )
        )

        usage_by_member_and_product = {}
        for subscription in get_active_and_future_subscriptions(
            subscription_start
        ).filter(member__in=members_at_pickup_location):
            if subscription.member not in usage_by_member_and_product.keys():
                usage_by_member_and_product[subscription.member] = {}
            if (
                subscription.product
                not in usage_by_member_and_product[subscription.member].keys()
            ):
                usage_by_member_and_product[subscription.member][
                    subscription.product
                ] = 0
            usage_by_member_and_product[subscription.member][subscription.product] = (
                max(
                    usage_by_member_and_product[subscription.member][
                        subscription.product
                    ],
                    product_id_to_basket_size_usage_map[subscription.product_id]
                    * subscription.quantity,
                )
            )

        total_usage = 0
        for usage_by_product in usage_by_member_and_product.values():
            for usage in usage_by_product.values():
                total_usage += usage

        return total_usage

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
