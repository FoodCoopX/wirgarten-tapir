from typing import Dict

from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import Subscription, ProductType, Product, ProductPrice


class TapirCache:
    @classmethod
    def get_all_subscriptions(cls, cache: Dict):
        return get_from_cache_or_compute(
            cache, "all_subscriptions", lambda: set(Subscription.objects.order_by("id"))
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
