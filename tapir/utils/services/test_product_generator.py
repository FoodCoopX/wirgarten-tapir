import datetime

from tapir.configuration.models import TapirParameter
from tapir.utils.config import Organization
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS, NO_DELIVERY
from tapir.wirgarten.models import (
    ProductType,
    Product,
    GrowingPeriod,
    ProductPrice,
    HarvestShareProduct,
    ProductCapacity,
    TaxRate,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class TestProductGenerator:
    @classmethod
    def generate_product(
        cls,
        product_type: ProductType,
        name: str,
        base_price: float,
        size: float,
        base: bool,
        min_coop_shares: int | None = None,
    ):
        if min_coop_shares is not None:
            product = HarvestShareProduct.objects.create(
                type=product_type, name=name, base=base, min_coop_shares=min_coop_shares
            )
        else:
            product = Product.objects.create(type=product_type, name=name, base=base)

        # prices were a bit cheaper last year
        start_of_previous_growing_period = (
            GrowingPeriod.objects.order_by("start_date").first().start_date
        )
        ProductPrice.objects.create(
            product=product,
            size=size,
            price=base_price * 0.9,
            valid_from=start_of_previous_growing_period,
        )

        # new prices are from 2 month ago
        ProductPrice.objects.create(
            product=product,
            size=size,
            price=base_price,
            valid_from=get_today() - datetime.timedelta(days=60),
        )

        # prices will be a bit more expensive next year
        start_of_next_growing_period = (
            GrowingPeriod.objects.order_by("-start_date").first().start_date
        )
        ProductPrice.objects.create(
            product=product,
            size=size,
            price=base_price * 1.1,
            valid_from=start_of_next_growing_period,
        )

    @classmethod
    def generate_products(cls, organization: Organization):
        ernteanteile = ProductType.objects.create(
            name="Ernteanteile", delivery_cycle=WEEKLY[0], is_affected_by_jokers=True
        )
        TaxRate.objects.create(
            product_type=ernteanteile,
            tax_rate=0,
            valid_from=GrowingPeriod.objects.order_by("start_date").first().start_date,
        )
        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=ernteanteile.id
        )
        cls.generate_product(
            product_type=ernteanteile,
            name="M",
            base_price=70.3,
            size=1,
            base=True,
            min_coop_shares=2,
        )
        cls.generate_product(
            product_type=ernteanteile,
            name="S",
            base_price=48.3,
            size=0.66,
            base=False,
            min_coop_shares=1,
        )
        cls.generate_product(
            product_type=ernteanteile,
            name="L",
            base_price=109.8,
            size=1.33,
            base=False,
            min_coop_shares=3,
        )
        if organization == Organization.WIRGARTEN:
            cls.generate_product(
                product_type=ernteanteile,
                name="XL",
                base_price=129.2,
                size=1.66,
                base=False,
                min_coop_shares=4,
            )

        eggs = ProductType.objects.create(
            name="Hühneranteile",
            delivery_cycle=EVEN_WEEKS[0],
            is_affected_by_jokers=True,
        )
        TaxRate.objects.create(
            product_type=eggs,
            tax_rate=0.07,
            valid_from=GrowingPeriod.objects.order_by("start_date").first().start_date,
        )
        cls.generate_product(
            product_type=eggs, name="Ganze", base_price=18, size=1, base=True
        )
        cls.generate_product(
            product_type=eggs, name="Halbe", base_price=9.5, size=0.5, base=False
        )

        hofpunkt = ProductType.objects.create(
            name="Hofpunkt", delivery_cycle=NO_DELIVERY[0], is_affected_by_jokers=False
        )
        TaxRate.objects.create(
            product_type=hofpunkt,
            tax_rate=0.07,
            valid_from=GrowingPeriod.objects.order_by("start_date").first().start_date,
        )
        cls.generate_product(
            product_type=hofpunkt,
            name="Mitgliedschaft",
            base_price=3,
            size=1,
            base=True,
        )

    @classmethod
    def generate_product_capacities(cls):
        for growing_period in GrowingPeriod.objects.all():
            for product_type in ProductType.objects.all():
                ProductCapacity.objects.create(
                    product_type=product_type,
                    period=growing_period,
                    capacity=1000,
                )

    @classmethod
    def generate_product_data(cls, organization: Organization):
        cls.generate_products(organization)
        cls.generate_product_capacities()
