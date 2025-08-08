import datetime

from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import ProductType


class TaxRateService:
    @classmethod
    def get_tax_rate(
        cls, product_type: ProductType, at_date: datetime.date, cache: dict
    ):
        tax_rates = TapirCache.get_product_type_tax_rates(
            product_type=product_type, cache=cache
        )
        tax_rates = list(tax_rates)
        tax_rates.sort(key=lambda x: x.valid_from, reverse=True)

        for tax_rate in tax_rates:
            if tax_rate.valid_from <= at_date:
                return tax_rate.tax_rate

        return 0.19
