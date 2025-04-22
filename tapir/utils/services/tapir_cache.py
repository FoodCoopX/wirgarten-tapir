import datetime
from typing import Dict, Set

from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import Subscription, ProductType, Product, ProductPrice


class TapirCache:
    @classmethod
    def get_all_subscriptions(cls, cache: Dict) -> Set[Subscription]:
        return get_from_cache_or_compute(
            cache, "all_subscriptions", lambda: set(Subscription.objects.order_by("id"))
        )

    @classmethod
    def get_subscriptions_active_at_date(
        cls, reference_date: datetime.date, cache: Dict
    ):
        def compute():
            all_subscriptions = cls.get_all_subscriptions(cache)
            return {
                subscription
                for subscription in all_subscriptions
                if subscription.start_date <= reference_date <= subscription.end_date
            }

        subscriptions_by_date = get_from_cache_or_compute(
            cache, "subscriptions_by_date", lambda: {}
        )
        return get_from_cache_or_compute(subscriptions_by_date, reference_date, compute)

    @classmethod
    def get_subscriptions_by_delivery_cycle(
        cls, cache: Dict, delivery_cycle
    ) -> Set[Subscription]:
        subscriptions_by_delivery_cycle = get_from_cache_or_compute(
            cache, "subscriptions_by_delivery_cycle", lambda: {}
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
        return get_from_cache_or_compute(
            cache,
            "subscriptions_affected_by_jokers",
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
        def compute():
            subscriptions_by_product_type = {
                product_type: set() for product_type in ProductType.objects.all()
            }
            subscriptions = Subscription.objects.select_related("product__type")
            for subscription in subscriptions:
                subscriptions_by_product_type[subscription.product.type].add(
                    subscription
                )
            return subscriptions_by_product_type

        return get_from_cache_or_compute(
            cache, "subscriptions_by_product_type", compute
        )

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
