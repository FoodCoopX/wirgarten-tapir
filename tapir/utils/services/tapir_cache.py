import datetime
from typing import Dict, Set

from tapir.payments.models import MemberPaymentRhythm
from tapir.utils.services.tapir_cache_manager import TapirCacheManager
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import (
    Subscription,
    ProductType,
    Product,
    ProductPrice,
    PickupLocation,
    PickupLocationOpeningTime,
    CoopShareTransaction,
    ProductCapacity,
    GrowingPeriod,
    Member,
)
from tapir.wirgarten.service.product_standard_order import product_type_order_by
from tapir.wirgarten.utils import get_today


class TapirCache:
    @classmethod
    def get_all_subscriptions(cls, cache: Dict) -> Set[Subscription]:
        key = "all_subscriptions"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )
        return get_from_cache_or_compute(
            cache, key, lambda: set(Subscription.objects.order_by("id"))
        )

    @classmethod
    def get_subscriptions_active_at_date(
        cls, reference_date: datetime.date, cache: Dict
    ):
        key = "subscriptions_by_date"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )

        def compute():
            all_subscriptions = cls.get_all_subscriptions(cache)
            return {
                subscription
                for subscription in all_subscriptions
                if subscription.start_date <= reference_date
                and (
                    subscription.end_date is None
                    or reference_date <= subscription.end_date
                )
            }

        subscriptions_by_date = get_from_cache_or_compute(cache, key, lambda: {})
        return get_from_cache_or_compute(subscriptions_by_date, reference_date, compute)

    @classmethod
    def get_active_and_future_subscriptions_by_member_id(
        cls, cache: dict, reference_date: datetime.date
    ):
        key = "subscriptions_by_date_and_member_id"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )

        def compute():
            from tapir.wirgarten.service.products import (
                get_active_and_future_subscriptions,
            )

            subscriptions_by_member_id = {}
            for subscription in get_active_and_future_subscriptions(
                reference_date=reference_date, cache=cache
            ):
                if subscription.member_id not in subscriptions_by_member_id.keys():
                    subscriptions_by_member_id[subscription.member_id] = []
                subscriptions_by_member_id[subscription.member_id].append(subscription)
            return subscriptions_by_member_id

        subscriptions_by_date_and_member_id = get_from_cache_or_compute(
            cache, key, lambda: {}
        )
        return get_from_cache_or_compute(
            subscriptions_by_date_and_member_id, reference_date, compute
        )

    @classmethod
    def get_subscriptions_by_delivery_cycle(
        cls, cache: Dict, delivery_cycle
    ) -> Set[Subscription]:
        key = "subscriptions_by_delivery_cycle"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )

        subscriptions_by_delivery_cycle = get_from_cache_or_compute(
            cache, key, lambda: {}
        )
        return get_from_cache_or_compute(
            subscriptions_by_delivery_cycle,
            delivery_cycle,
            lambda: set(
                Subscription.objects.filter(
                    product__type__delivery_cycle=delivery_cycle
                ).order_by("id")
            ),
        )

    @classmethod
    def get_subscriptions_affected_by_jokers(cls, cache: Dict):
        key = "subscriptions_affected_by_jokers"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )

        return get_from_cache_or_compute(
            cache,
            key,
            lambda: Subscription.objects.filter(
                product__type__is_affected_by_jokers=True
            ),
        )

    @classmethod
    def get_product_type_by_id(cls, cache: Dict, product_type_id: str):
        product_types_by_id = get_from_cache_or_compute(
            cache, "product_types_by_id", lambda: {}
        )
        return get_from_cache_or_compute(
            product_types_by_id,
            product_type_id,
            lambda: ProductType.objects.get(id=product_type_id),
        )

    @classmethod
    def get_products_with_product_type(cls, cache: Dict, product_type_id: str):
        product_by_product_type_id = get_from_cache_or_compute(
            cache, "product_by_product_type_id", lambda: {}
        )

        return get_from_cache_or_compute(
            product_by_product_type_id,
            product_type_id,
            lambda: set(Product.objects.filter(type_id=product_type_id)),
        )

    @classmethod
    def get_product_prices_by_product_id(cls, cache: Dict, product_id: str):
        product_prices_by_product_id = get_from_cache_or_compute(
            cache, "product_prices_by_product_id", lambda: {}
        )

        def compute():
            return set(
                ProductPrice.objects.filter(product_id=product_id).order_by(
                    "valid_from"
                )
            )

        return get_from_cache_or_compute(
            product_prices_by_product_id,
            product_id,
            compute,
        )

    @classmethod
    def get_all_products(cls, cache: Dict):
        return get_from_cache_or_compute(
            cache, "all_products", lambda: set(Product.objects.order_by("id"))
        )

    @classmethod
    def get_subscriptions_by_product_type(cls, cache: Dict):
        key = "subscriptions_by_product_type"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )

        def compute():
            subscriptions_by_product_type = {
                product_type: set()
                for product_type in ProductType.objects.order_by(
                    *product_type_order_by(cache=cache)
                )
            }
            subscriptions = Subscription.objects.select_related("product__type")
            for subscription in subscriptions:
                subscriptions_by_product_type[subscription.product.type].add(
                    subscription
                )
            return subscriptions_by_product_type

        return get_from_cache_or_compute(cache, key, compute)

    @classmethod
    def get_product_by_name_iexact(cls, cache: Dict, product_name: str):
        products = cls.get_all_products(cache)

        products_by_name_iexact = get_from_cache_or_compute(
            cache, "products_by_name_iexact", lambda: {}
        )

        def name_matches(product: Product):
            return product.name.casefold() == product_name.casefold()

        return get_from_cache_or_compute(
            products_by_name_iexact,
            product_name,
            lambda: next(filter(name_matches, products), None),
        )

    @classmethod
    def get_last_subscription(cls, cache: Dict):
        key = "last_subscription"
        TapirCacheManager.register_key_in_category(
            cache=cache, key=key, category="subscriptions"
        )

        return get_from_cache_or_compute(
            cache,
            key,
            lambda: Subscription.objects.filter(end_date__isnull=False)
            .order_by("end_date")
            .last(),
        )

    @classmethod
    def get_product_types_in_standard_order(cls, cache: Dict):
        return get_from_cache_or_compute(
            cache,
            "product_types_in_standard_order",
            lambda: ProductType.objects.order_by(*product_type_order_by(cache=cache)),
        )

    @classmethod
    def get_pickup_location_by_id(cls, cache: Dict, pickup_location_id):
        if pickup_location_id is None:
            return None

        def compute():
            return {
                pickup_location.id: pickup_location
                for pickup_location in PickupLocation.objects.all()
            }

        pickup_location_by_id_cache = get_from_cache_or_compute(
            cache, "pickup_location_by_id", lambda: compute()
        )
        return pickup_location_by_id_cache.get(pickup_location_id, None)

    @classmethod
    def get_product_by_id(cls, cache: Dict, product_id):
        if product_id is None:
            return None

        def compute():
            return {product.id: product for product in Product.objects.all()}

        product_by_id_cache = get_from_cache_or_compute(
            cache, "product_by_id", lambda: compute()
        )
        return product_by_id_cache.get(product_id, None)

    @classmethod
    def get_opening_times_by_pickup_location_id(cls, cache: Dict, pickup_location_id):
        opening_times_by_pickup_location_id_cache = get_from_cache_or_compute(
            cache, "opening_times_by_pickup_location_id", lambda: {}
        )
        return get_from_cache_or_compute(
            opening_times_by_pickup_location_id_cache,
            pickup_location_id,
            lambda: list(
                PickupLocationOpeningTime.objects.filter(
                    pickup_location_id=pickup_location_id
                )
            ),
        )

    @classmethod
    def get_unconfirmed_coop_share_purchases_by_member_id(cls, cache: dict):
        def compute():
            transactions = cls.get_unconfirmed_coop_share_purchases(cache=cache)
            transactions_by_member_id = {}
            for transaction in transactions:
                if transaction.member_id not in transactions_by_member_id.keys():
                    transactions_by_member_id[transaction.member_id] = []
                transactions_by_member_id[transaction.member_id].append(transaction)
            return transactions_by_member_id

        return get_from_cache_or_compute(
            cache, "unconfirmed_coop_share_transactions_by_member_id", compute
        )

    @classmethod
    def get_unconfirmed_coop_share_purchases(cls, cache: dict):
        return get_from_cache_or_compute(
            cache,
            "unconfirmed_coop_share_purchases",
            lambda: list(
                CoopShareTransaction.objects.filter(
                    admin_confirmed__isnull=True,
                    transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
                )
            ),
        )

    @classmethod
    def get_product_type_capacity_at_date(
        cls, cache: dict, product_type: ProductType, reference_date: datetime.date
    ):
        product_type_capacities_by_growing_period = get_from_cache_or_compute(
            cache, "product_type_capacities_by_growing_period", lambda: {}
        )
        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=reference_date, cache=cache
        )

        def compute():
            return ProductCapacity.objects.filter(
                product_type=product_type, period=growing_period
            ).first()

        return get_from_cache_or_compute(
            product_type_capacities_by_growing_period,
            growing_period,
            compute,
        )

    @classmethod
    def get_growing_period_at_date(
        cls, reference_date: datetime.date, cache: Dict
    ) -> GrowingPeriod | None:
        if reference_date is None:
            reference_date = get_today(cache=cache)

        def compute():
            growing_periods = get_from_cache_or_compute(
                cache,
                "all_growing_periods",
                lambda: set(GrowingPeriod.objects.order_by("start_date")),
            )
            for growing_period in growing_periods:
                if (
                    growing_period.start_date
                    <= reference_date
                    <= growing_period.end_date
                ):
                    return growing_period
            return None

        growing_periods_by_date_cache = get_from_cache_or_compute(
            cache, "growing_periods_by_date", lambda: {}
        )
        return get_from_cache_or_compute(
            growing_periods_by_date_cache, reference_date, compute
        )

    @classmethod
    def get_payment_rhythms_objects_by_member(
        cls, cache: dict
    ) -> dict[Member, list[MemberPaymentRhythm]]:
        def compute():
            result = {}
            all_rhythms = MemberPaymentRhythm.objects.select_related("member").order_by(
                "valid_from"
            )
            for rhythm in all_rhythms:
                if rhythm.member not in result.keys():
                    result[rhythm.member] = []
                result[rhythm.member].append(rhythm)
            return result

        return get_from_cache_or_compute(cache, "payment_rhythms_by_member", compute)

    @classmethod
    def get_member_payment_rhythm_object(
        cls, member: Member, reference_date: datetime.date, cache: dict
    ):
        payment_rhythms_by_member = cls.get_payment_rhythms_objects_by_member(
            cache=cache
        )
        member_payment_rhythms = payment_rhythms_by_member.get(member, [])

        rhythm_at_date = None
        for rhythm in member_payment_rhythms:
            # member_payment_rhythms is assumed sorted by valid_from ascending
            if rhythm.valid_from <= reference_date:
                rhythm_at_date = rhythm

        return rhythm_at_date
