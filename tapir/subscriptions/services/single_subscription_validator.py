from icecream import ic

from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache


class SingleSubscriptionValidator:
    @classmethod
    def are_single_subscription_products_are_ordered_at_most_once(
        cls, order: TapirOrder, cache: dict
    ):
        ordered_product_type_ids = {product.type_id for product in order.keys()}
        for product_type_id in ordered_product_type_ids:
            product_type = TapirCache.get_product_type_by_id(
                cache=cache, product_type_id=product_type_id
            )
            if not product_type.single_subscription_only:
                continue

            total_quantity = 0
            for product, quantity in order.items():
                if product.type_id == product_type_id:
                    total_quantity += quantity

            if total_quantity > 1:
                ic(product_type, order)
                return False

        return True
