import datetime
from typing import Dict

from tapir.pickup_locations.services.share_capacities_service import (
    SharesCapacityService,
)
from tapir.wirgarten.forms.pickup_location import get_current_capacity_usage
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    Product,
    PickupLocationCapability,
    ProductType,
)
from tapir.wirgarten.service.products import get_active_subscriptions, get_product_price


class PickupLocationCapacityModeShareChecker:
    @classmethod
    def check_for_picking_mode_share(
        cls,
        pickup_location: PickupLocation,
        ordered_product_to_quantity_map: Dict[Product, int],
        already_registered_member: Member | None,
        subscription_start: datetime.date,
    ) -> bool:
        product_type_to_available_capacity_map = SharesCapacityService.get_available_share_capacities_for_pickup_location_by_product_type(
            pickup_location
        )

        for (
            product_type,
            available_capacity,
        ) in product_type_to_available_capacity_map.items():
            if not cls.check_capacity_for_product_type(
                product_type=product_type,
                available_capacity=available_capacity,
                member=already_registered_member,
                pickup_location=pickup_location,
                subscription_start=subscription_start,
                ordered_product_to_quantity_map=ordered_product_to_quantity_map,
            ):
                return False

        return True

    @classmethod
    def check_capacity_for_product_type(
        cls,
        product_type: ProductType,
        available_capacity: int,
        member: Member | None,
        pickup_location: PickupLocation,
        subscription_start: datetime.date,
        ordered_product_to_quantity_map: Dict[Product, int],
    ):
        current_usage = cls.get_current_capacity_usage(
            pickup_location, product_type, subscription_start
        )
        amount_used_by_member_before_changes = (
            cls.get_capacity_used_by_member_before_changes(
                member, subscription_start, product_type
            )
        )
        capacity_used_by_the_order = (
            cls.calculate_capacity_used_by_the_ordered_products(
                ordered_product_to_quantity_map, product_type, subscription_start
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
        product_type: ProductType,
        subscription_start: datetime.date,
    ):
        return get_current_capacity_usage(
            capability=PickupLocationCapability.objects.get(
                pickup_location=pickup_location, product_type=product_type
            ),
            reference_date=subscription_start,
        )

    @classmethod
    def get_capacity_used_by_member_before_changes(
        cls,
        member: Member | None,
        subscription_start: datetime.date,
        product_type: ProductType,
    ):
        if member is None:
            return 0

        return float(
            sum(
                [
                    s.get_used_capacity()
                    for s in get_active_subscriptions(subscription_start).filter(
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
    ):
        total = 0.0
        for ordered_product, quantity in ordered_product_to_quantity_map.items():
            if ordered_product.type != product_type:
                continue
            total += (
                float(get_product_price(ordered_product, reference_date).size)
                * quantity
            )
        return total
