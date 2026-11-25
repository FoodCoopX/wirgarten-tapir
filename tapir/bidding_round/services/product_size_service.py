from decimal import Decimal

from tapir.wirgarten.models import GrowingPeriod, Product
from tapir.wirgarten.service.products import get_product_price


class ProductSizeService:
    """Share size of a product, read from its price for the growing period."""

    @classmethod
    def get_size(
        cls, product: Product, growing_period: GrowingPeriod, cache: dict
    ) -> Decimal | None:
        product_price = get_product_price(
            product=product, reference_date=growing_period.start_date, cache=cache
        )
        if product_price is None or not product_price.size:
            return None
        return Decimal(str(product_price.size))
