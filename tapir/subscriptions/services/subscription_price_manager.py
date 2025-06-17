from datetime import datetime

from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.service.products import get_product_price


class SubscriptionPriceManager:
    @staticmethod
    def get_monthly_price_of_order_without_solidarity(
        order: TapirOrder,
        reference_date: datetime.date,
        cache: dict = None,
    ):
        total = 0.0
        for product, quantity in order:
            product_price_object = get_product_price(
                product=product, reference_date=reference_date, cache=cache
            )
            total += float(product_price_object.price) * quantity
        return total
