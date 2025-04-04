import datetime
from typing import Dict, Callable

from django.db.models import OuterRef, Subquery, DecimalField, F, Sum

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.pickup_locations.services.share_capacities_service import (
    SharesCapacityService,
)
from tapir.utils.shortcuts import get_monday, get_from_cache_or_compute
from tapir.wirgarten.models import (
    Member,
    PickupLocation,
    Product,
    ProductType,
    ProductPrice,
    Subscription,
    MemberPickupLocation,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_product_price,
    get_current_growing_period,
)


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
        member: Member | None,
        pickup_location: PickupLocation,
        subscription_start: datetime.date,
        ordered_product_to_quantity_map: Dict[Product, int],
        parameter_cache: Dict | None = None,
    ):
        free_capacity = cls.get_free_capacity_at_date(
            product_type=product_type,
            pickup_location=pickup_location,
            reference_date=subscription_start,
        )

        amount_used_by_member_before_changes = (
            cls.get_capacity_used_by_member_before_changes(
                member=member,
                subscription_start=subscription_start,
                product_type=product_type,
                parameter_cache=parameter_cache,
            )
        )
        capacity_used_by_the_order = (
            cls.calculate_capacity_used_by_the_ordered_products(
                ordered_product_to_quantity_map=ordered_product_to_quantity_map,
                product_type=product_type,
                reference_date=subscription_start,
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
        cache: Dict | None = None,
    ):
        members_at_pickup_location = (
            MemberPickupLocationService.get_members_at_pickup_location(
                pickup_location, reference_date
            )
        )

        subscriptions_active_at_reference_date = get_active_subscriptions(
            reference_date,
            get_from_cache_or_compute(cache, "parameter_cache", lambda: None),
        ).filter(member__in=members_at_pickup_location, product__type=product_type)

        relevant_subscriptions = subscriptions_active_at_reference_date
        if get_parameter_value(
            Parameter.SUBSCRIPTION_AUTOMATIC_RENEWAL,
            get_from_cache_or_compute(cache, "parameter_cache", lambda: None),
        ):
            relevant_subscriptions = cls.extend_subscriptions_with_those_that_will_be_renewed(
                subscriptions_active_at_reference_date=subscriptions_active_at_reference_date,
                reference_date=reference_date,
                product_type=product_type,
                members_at_pickup_location=members_at_pickup_location,
                cache=cache,
            )

        latest_valid_product_price = (
            ProductPrice.objects.filter(
                product=OuterRef("product"), valid_from__lte=reference_date
            )
            .order_by("-valid_from")
            .values("size")[:1]
        )

        subscriptions_annotated_with_total_size = relevant_subscriptions.annotate(
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
    def extend_subscriptions_with_those_that_will_be_renewed(
        cls,
        subscriptions_active_at_reference_date,
        reference_date: datetime.date,
        product_type: ProductType,
        members_at_pickup_location,
        cache: Dict | None = None,
    ):
        relevant_subscriptions = set(subscriptions_active_at_reference_date)

        current_growing_period = get_current_growing_period(
            reference_date,
            get_from_cache_or_compute(cache, "growing_period_at_date", lambda: {}),
        )

        products_by_product_type_cache = get_from_cache_or_compute(
            cache, "products_by_product_type", lambda: {}
        )
        products = get_from_cache_or_compute(
            products_by_product_type_cache,
            product_type,
            lambda: Product.objects.filter(type=product_type),
        )

        for product in products:
            members_that_have_a_subscription_of_product_at_reference_date = (
                subscriptions_active_at_reference_date.filter(
                    product=product
                ).values_list("member", flat=True)
            )
            subscriptions_that_will_get_renewed = (
                get_active_subscriptions(
                    current_growing_period.start_date - datetime.timedelta(days=1),
                    get_from_cache_or_compute(cache, "parameter_cache", lambda: None),
                )
                .filter(
                    member__in=members_at_pickup_location,
                    cancellation_ts__isnull=True,
                    product=product,
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
        product_type: ProductType,
        parameter_cache: Dict | None = None,
    ):
        if member is None:
            return 0

        return float(
            sum(
                [
                    s.get_used_capacity()
                    for s in get_active_subscriptions(
                        subscription_start, parameter_cache
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

    @classmethod
    def get_highest_usage_after_date_generic(
        cls,
        pickup_location: PickupLocation,
        reference_date: datetime.date,
        lambda_get_usage_at_date: Callable,
        cache: Dict,
    ):
        current_date = reference_date
        max_usage = 0

        usage_at_date_cache = get_from_cache_or_compute(
            cache, "usage_at_date_cache", lambda: {}
        )
        date_of_last_possible_capacity_change = get_from_cache_or_compute(
            cache,
            "date_of_last_possible_capacity_change",
            lambda: cls.get_date_of_last_possible_capacity_change(pickup_location),
        )

        while current_date < date_of_last_possible_capacity_change:
            usage_at_date = get_from_cache_or_compute(
                usage_at_date_cache,
                current_date,
                lambda: lambda_get_usage_at_date(current_date),
            )

            max_usage = max(
                max_usage,
                usage_at_date,
            )

            current_date = get_monday(current_date + datetime.timedelta(days=7))

        return max_usage

    @classmethod
    def get_highest_usage_after_date(
        cls,
        pickup_location: PickupLocation,
        product_type: ProductType,
        reference_date: datetime.date,
        cache: Dict,
    ):
        return cls.get_highest_usage_after_date_generic(
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

    @staticmethod
    def get_date_of_last_possible_capacity_change(pickup_location: PickupLocation):
        last_pickup_location_change = (
            MemberPickupLocation.objects.filter(pickup_location=pickup_location)
            .order_by("valid_from")
            .last()
        )
        last_subscription = Subscription.objects.order_by("end_date").last()
        if not last_pickup_location_change:
            return last_subscription.end_date
        if not last_subscription:
            return last_pickup_location_change.valid_from
        return max(
            last_pickup_location_change.valid_from,
            last_subscription.end_date,
        )

    @classmethod
    def get_free_capacity_at_date(
        cls,
        product_type: ProductType,
        pickup_location: PickupLocation,
        reference_date: datetime.date,
        cache: Dict | None = None,
    ):
        if cache is None:
            cache = {}

        product_type_to_available_capacity_map = get_from_cache_or_compute(
            cache,
            "product_type_to_available_capacity_map",
            lambda: SharesCapacityService.get_available_share_capacities_for_pickup_location_by_product_type(
                pickup_location
            ),
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
