import datetime
from typing import Dict

from django.db.models import OuterRef, Subquery, DecimalField, F, Sum

from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.pickup_locations.services.share_capacities_service import (
    SharesCapacityService,
)
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    Product,
    ProductType,
    ProductPrice,
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
            if available_capacity is None:
                # if the capacity in None, the location has unlimited capacity
                continue

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
        current_usage = cls.get_capacity_usage_at_date(
            pickup_location=pickup_location,
            product_type=product_type,
            reference_date=subscription_start,
        )
        amount_used_by_member_before_changes = (
            cls.get_capacity_used_by_member_before_changes(
                member=member,
                subscription_start=subscription_start,
                product_type=product_type,
            )
        )
        capacity_used_by_the_order = (
            cls.calculate_capacity_used_by_the_ordered_products(
                ordered_product_to_quantity_map=ordered_product_to_quantity_map,
                product_type=product_type,
                reference_date=subscription_start,
            )
        )
        capacity_usage_after_changes = (
            current_usage
            - amount_used_by_member_before_changes
            + capacity_used_by_the_order
        )
        return capacity_usage_after_changes <= available_capacity

    @classmethod
    def get_capacity_usage_at_date(
        cls,
        pickup_location: PickupLocation,
        product_type: ProductType,
        reference_date: datetime.date,
    ):
        members_at_pickup_location = MemberPickupLocationService.annotate_member_queryset_with_pickup_location_at_date(
            Member.objects.all(), reference_date
        ).filter(
            **{
                MemberPickupLocationService.ANNOTATION_CURRENT_PICKUP_LOCATION_ID: pickup_location.id
            }
        )

        subscriptions = get_active_subscriptions(reference_date).filter(
            member__in=members_at_pickup_location, product__type=product_type
        )
        latest_valid_product_price = (
            ProductPrice.objects.filter(
                product=OuterRef("product"), valid_from__lte=reference_date
            )
            .order_by("-valid_from")
            .values("size")[:1]
        )

        subscriptions_annotated_with_total_size = subscriptions.annotate(
            latest_size=Subquery(
                latest_valid_product_price,
                output_field=DecimalField(decimal_places=4),
            ),
            total_size_per_subscription=F("latest_size") * F("quantity"),
        )

        total_size = subscriptions_annotated_with_total_size.aggregate(
            total_size=Sum("total_size_per_subscription")
        )["total_size"]

        return float(total_size) if total_size else 0

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
