import datetime

from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.utils.config import Organization
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS, NO_DELIVERY, EVERY_FOUR_WEEKS
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


class ProductGenerator:
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

        match organization:
            case Organization.WIRGARTEN:
                cls.generate_products_wirgarten(product_type_ernteanteile=ernteanteile)
            case Organization.BIOTOP:
                cls.generate_products_biotop(product_type_ernteanteile=ernteanteile)
            case Organization.VEREIN:
                cls.generate_products_verein(product_type_ernteanteile=ernteanteile)
            case Organization.L2G:
                cls.generate_products_l2g(product_type_ernteanteile=ernteanteile)
            case Organization.MM:
                cls.generate_products_mm(product_type_ernteanteile=ernteanteile)
            case _:
                raise ImproperlyConfigured(f"Unknown organization type: {organization}")

    @classmethod
    def generate_products_verein(cls, product_type_ernteanteile: ProductType):
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="M",
            base_price=70.3,
            size=1,
            base=True,
            min_coop_shares=2,
        )
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="S",
            base_price=48.3,
            size=0.66,
            base=False,
            min_coop_shares=1,
        )
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="L",
            base_price=109.8,
            size=1.33,
            base=False,
            min_coop_shares=3,
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

        association_membership = ProductType.objects.create(
            name="Vereinsmitgliedschaft",
            delivery_cycle=NO_DELIVERY[0],
            is_affected_by_jokers=False,
            single_subscription_only=True,
            subscriptions_have_end_dates=False,
            must_be_subscribed_to=True,
            is_association_membership=True,
        )
        TaxRate.objects.create(
            product_type=association_membership,
            tax_rate=0,
            valid_from=GrowingPeriod.objects.order_by("start_date").first().start_date,
        )
        cls.generate_product(
            product_type=association_membership,
            name="Typ A",
            base_price=10,
            size=1,
            base=True,
        )
        cls.generate_product(
            product_type=association_membership,
            name="Typ B",
            base_price=17.5,
            size=1,
            base=False,
        )
        cls.generate_product(
            product_type=association_membership,
            name="Typ C",
            base_price=22.5,
            size=1,
            base=False,
        )

    @classmethod
    def generate_products_wirgarten(cls, product_type_ernteanteile: ProductType):
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="M",
            base_price=70.3,
            size=1,
            base=True,
            min_coop_shares=2,
        )
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="S",
            base_price=48.3,
            size=0.66,
            base=False,
            min_coop_shares=1,
        )
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="L",
            base_price=109.8,
            size=1.3,
            base=False,
            min_coop_shares=3,
        )
        cls.generate_product(
            product_type=product_type_ernteanteile,
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
            name="Hofpunkt",
            delivery_cycle=NO_DELIVERY[0],
            is_affected_by_jokers=False,
            single_subscription_only=True,
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
    def generate_products_biotop(cls, product_type_ernteanteile: ProductType):
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="M",
            base_price=70.3,
            size=2,
            base=True,
            min_coop_shares=2,
        )
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="S",
            base_price=48.3,
            size=1.5,
            base=False,
            min_coop_shares=1,
        )
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="L",
            base_price=109.8,
            size=3.5,
            base=False,
            min_coop_shares=3,
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
            name="Hofpunkt",
            delivery_cycle=NO_DELIVERY[0],
            is_affected_by_jokers=False,
            single_subscription_only=True,
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

        ProductBasketSizeEquivalence.objects.create(
            product=Product.objects.get(name="S"),
            basket_size_name="kleine Kiste",
            quantity=1,
        )
        ProductBasketSizeEquivalence.objects.create(
            product=Product.objects.get(name="M"),
            basket_size_name="normale Kiste",
            quantity=1,
        )
        ProductBasketSizeEquivalence.objects.create(
            product=Product.objects.get(name="L"),
            basket_size_name="kleine Kiste",
            quantity=1,
        )
        ProductBasketSizeEquivalence.objects.create(
            product=Product.objects.get(name="L"),
            basket_size_name="normale Kiste",
            quantity=1,
        )

    @classmethod
    def generate_products_l2g(cls, product_type_ernteanteile: ProductType):
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="Klein",
            base_price=72,
            size=1,
            base=True,
            min_coop_shares=2,
        )
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="Groß",
            base_price=112,
            size=1.6,
            base=False,
            min_coop_shares=4,
        )

        bread = ProductType.objects.create(
            name="Brot",
            delivery_cycle=WEEKLY[0],
            is_affected_by_jokers=True,
        )
        TaxRate.objects.create(
            product_type=bread,
            tax_rate=0.07,
            valid_from=GrowingPeriod.objects.order_by("start_date").first().start_date,
        )
        cls.generate_product(
            product_type=bread, name="Vollkornbrot", base_price=27, size=1, base=True
        )
        cls.generate_product(
            product_type=bread,
            name="Glutenfreies Vollkornbrot",
            base_price=27,
            size=1,
            base=False,
        )

        honey = ProductType.objects.create(
            name="Honig",
            delivery_cycle=EVERY_FOUR_WEEKS[0],
            is_affected_by_jokers=True,
        )
        TaxRate.objects.create(
            product_type=honey,
            tax_rate=0.07,
            valid_from=GrowingPeriod.objects.order_by("start_date").first().start_date,
        )
        cls.generate_product(
            product_type=honey, name="Honig", base_price=7, size=1, base=True
        )

        oil = ProductType.objects.create(
            name="Leinöl",
            delivery_cycle=EVERY_FOUR_WEEKS[0],
            is_affected_by_jokers=True,
        )
        TaxRate.objects.create(
            product_type=oil,
            tax_rate=0.07,
            valid_from=GrowingPeriod.objects.order_by("start_date").first().start_date,
        )
        cls.generate_product(
            product_type=oil,
            name="Frisches, kaltgepresstes Leinöl",
            base_price=11,
            size=1,
            base=True,
        )

    @classmethod
    def generate_product_capacities(cls):
        capacities = []
        for growing_period in GrowingPeriod.objects.all():
            for product_type in ProductType.objects.all():
                capacities.append(
                    ProductCapacity(
                        product_type=product_type,
                        period=growing_period,
                        capacity=1000,
                    )
                )
        ProductCapacity.objects.bulk_create(capacities)

    @classmethod
    def generate_product_data(cls, organization: Organization):
        cls.generate_products(organization)
        cls.generate_product_capacities()

    @classmethod
    def generate_products_mm(cls, product_type_ernteanteile: ProductType):
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="Ernteanteil ab Hof",
            base_price=75,
            size=1,
            base=True,
            min_coop_shares=2,
        )
        cls.generate_product(
            product_type=product_type_ernteanteile,
            name="Ernteanteil ab Depot",
            base_price=90,
            size=1,
            base=False,
            min_coop_shares=2,
        )
