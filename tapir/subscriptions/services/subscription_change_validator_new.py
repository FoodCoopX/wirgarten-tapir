import datetime

from tapir.wirgarten.models import Product
from tapir.wirgarten.service.products import get_product_price


class SubscriptionChangeValidatorNew:
    @classmethod
    def calculate_global_capacity_used_by_the_ordered_products(
        cls,
        ordered_products_to_quantity_map: dict[Product, int],
        reference_date: datetime.date,
        cache: dict = None,
    ):
        total = 0.0
        for product, quantity in ordered_products_to_quantity_map:
            product_price_object = get_product_price(
                product=product, reference_date=reference_date, cache=cache
            )
            total += float(product_price_object.size) * quantity
        return total
