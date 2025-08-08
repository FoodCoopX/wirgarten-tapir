import datetime
from decimal import Decimal
from typing import List, Dict

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q

from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.services.tapir_cache_manager import TapirCacheManager
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.models import (
    GrowingPeriod,
    Payable,
    Product,
    ProductCapacity,
    ProductPrice,
    ProductType,
    Subscription,
    TaxRate,
)
from tapir.wirgarten.service.product_standard_order import product_type_order_by
from tapir.wirgarten.utils import get_today
from tapir.wirgarten.validators import (
    validate_date_range,
    validate_growing_period_overlap,
)


def get_total_price_for_subs(subs: List[Payable], cache: Dict) -> float:
    """
    Returns the total amount of one payment for the given list of subs.

    :param subs: the list of subs (e.g. that are currently active for a user)
    :return: the total price in €
    """
    if not subs:
        return 0

    return round(sum([x.total_price(cache=cache) for x in subs]), 2)


def get_active_product_types(
    reference_date: datetime.date = None, cache: Dict = None
) -> iter:
    """
    Returns the product types which are active for the given reference date.

    :param reference_date: default: today()
    :return: the QuerySet of ProductTypes filtered for the given reference date
    """
    if reference_date is None:
        reference_date = get_today(cache=cache)

    def compute():
        return ProductType.objects.filter(
            id__in=ProductCapacity.objects.filter(
                period__start_date__lte=reference_date,
                period__end_date__gte=reference_date,
            ).values("product_type__id")
        ).order_by(*product_type_order_by(cache=cache))

    active_product_types_by_date_cache = get_from_cache_or_compute(
        cache, "active_product_types_by_date", lambda: {}
    )

    return get_from_cache_or_compute(
        active_product_types_by_date_cache, reference_date, compute
    )


def get_available_product_types(
    reference_date: datetime.date = None, cache: Dict = None
) -> list:
    if reference_date is None:
        reference_date = get_today(cache=cache)

    product_types = get_active_product_types(reference_date, cache=cache)
    return [
        p
        for p in product_types
        if is_product_type_available(p, reference_date, cache=cache)
    ]


def get_next_growing_period(
    reference_date: datetime.date = None, cache: Dict = None
) -> GrowingPeriod | None:
    if reference_date is None:
        reference_date = get_today(cache=cache)

    def compute():
        return (
            GrowingPeriod.objects.filter(start_date__gt=reference_date)
            .order_by("start_date")
            .first()
        )

    next_growing_periods_by_date_cache = get_from_cache_or_compute(
        cache, "next_growing_periods_by_date", lambda: {}
    )

    return get_from_cache_or_compute(
        next_growing_periods_by_date_cache, reference_date, compute
    )


@transaction.atomic
def create_growing_period(
    start_date: datetime.date,
    end_date: datetime.date,
    max_jokers_per_member: int,
    joker_restrictions: str,
) -> GrowingPeriod:
    """
    Creates a new growing period with the given start and end dates

    :param start_date: the start of the growing period
    :param end_date: the end of the growing period
    :return: the persisted instance
    """

    validate_date_range(start_date, end_date)
    validate_growing_period_overlap(start_date, end_date)

    return GrowingPeriod.objects.create(
        start_date=start_date,
        end_date=end_date,
        max_jokers_per_member=max_jokers_per_member,
        joker_restrictions=joker_restrictions,
    )


@transaction.atomic
def copy_growing_period(
    growing_period_id: str, start_date: datetime.date, end_date: datetime.date
):
    """
    Creates a new growing period and copies all product capacities from the given growing period.

    :param growing_period_id: the original growing period id
    :param start_date: the start of the new growing period
    :param end_date: the end of the new growing period
    """

    source_growing_period = GrowingPeriod.objects.get(id=growing_period_id)
    new_growing_period = create_growing_period(
        start_date=start_date,
        end_date=end_date,
        max_jokers_per_member=source_growing_period.max_jokers_per_member,
        joker_restrictions=source_growing_period.joker_restrictions,
    )
    ProductCapacity.objects.bulk_create(
        map(
            lambda x: ProductCapacity(
                period_id=new_growing_period.id,
                product_type=x.product_type,
                capacity=x.capacity,
            ),
            ProductCapacity.objects.filter(period_id=growing_period_id),
        )
    )

    return new_growing_period


@transaction.atomic
def delete_growing_period_with_capacities(growing_period_id: str) -> bool:
    """
    Deletes the growing period and its capacities.
    If the growing period does not start in the future, nothing will be deleted and the function returns False.

    :param growing_period_id: the id of the growing period to delete
    :return: True, if delete was successful
    """

    gp = GrowingPeriod.objects.get(id=growing_period_id)
    today = get_today()

    if gp.start_date < today:  # period does not start in the future
        return False

    ProductCapacity.objects.filter(period=gp).delete()
    gp.delete()
    return True


def get_active_product_capacities(
    reference_date: datetime.date = None, cache: Dict = None
):
    """
    Gets the active product capacities for the given reference date.

    :param reference_date: the date on which the capacity must be active
    :return: queryset of active product capacities
    """
    if reference_date is None:
        reference_date = get_today(cache=cache)

    def compute():
        return ProductCapacity.objects.filter(
            period__start_date__lte=reference_date, period__end_date__gte=reference_date
        ).order_by(
            *product_type_order_by("product_type_id", "product_type__name", cache=cache)
        )

    active_product_capacities_by_date_cache = get_from_cache_or_compute(
        cache, "active_product_capacities_by_date", lambda: {}
    )
    return get_from_cache_or_compute(
        active_product_capacities_by_date_cache, reference_date, compute
    )


def get_active_and_future_subscriptions(
    reference_date: datetime.date = None, cache: Dict | None = None
):
    """
    Gets active and future subscriptions. Future means e.g.: user just signed up and the contract starts next month

    :param reference_date: the date on which the capacity must be active
    :return: queryset of active and future subscriptions
    """
    if reference_date is None:
        reference_date = get_today(cache)

    def compute():
        filters = Q(end_date__gte=reference_date) | Q(end_date__isnull=True)
        return Subscription.objects.filter(filters).order_by(
            *product_type_order_by("product__type_id", "product__type__name", cache)
        )

    key = "active_and_future_subscriptions_by_date"
    TapirCacheManager.register_key_in_category(
        cache=cache, key=key, category="subscriptions"
    )
    active_and_future_subscriptions_by_date_cache = get_from_cache_or_compute(
        cache, key, lambda: {}
    )
    return get_from_cache_or_compute(
        active_and_future_subscriptions_by_date_cache, reference_date, compute
    )


def get_active_subscriptions(
    reference_date: datetime.date = None, cache: Dict | None = None
):
    """
    Gets currently active subscriptions. Subscriptions that are ordered but starting next month are not included!
    """
    if reference_date is None:
        reference_date = get_today(cache)

    def compute():
        return get_active_and_future_subscriptions(reference_date, cache).filter(
            start_date__lte=reference_date
        )

    key = "active_subscriptions_by_date"
    TapirCacheManager.register_key_in_category(
        cache=cache, key=key, category="subscriptions"
    )
    active_subscriptions_by_date_cache = get_from_cache_or_compute(
        cache, "active_subscriptions_by_date", lambda: {}
    )
    return get_from_cache_or_compute(
        active_subscriptions_by_date_cache, reference_date, compute
    )


@transaction.atomic
def create_product(
    name: str, price: Decimal, size: float, capacity_id: str, base=False
):
    """
    Creates a product and product price with the given attributes.

    :param name: the name of the product
    :param price: the price
    :param capacity_id: gets information about the growing period and product type via the capacity
    :param base: whether the product is the base product
    :return: the newly created product
    """
    pc = ProductCapacity.objects.get(id=capacity_id)

    if base:
        Product.objects.filter(type_id=pc.product_type.id, base=True).update(base=False)

    product = Product.objects.create(name=name, type_id=pc.product_type.id, base=base)

    ProductPrice.objects.create(
        price=price,
        product=product,
        valid_from=get_next_product_price_change_date(growing_period_id=pc.period.id),
        size=size,
    )

    return product


def get_product_price(
    product: str | Product,
    reference_date: datetime.date = None,
    cache: Dict | None = None,
) -> ProductPrice | None:
    """
    Returns the currently active product price.
    """
    if reference_date is None:
        reference_date = get_today(cache)
    if isinstance(product, Product):
        product = product.id

    cache_for_this_product = get_from_cache_or_compute(cache, product, lambda: {})
    price_by_date_cache = get_from_cache_or_compute(
        cache_for_this_product, "price_by_date", lambda: {}
    )

    def get_price():
        prices = list(TapirCache.get_product_prices_by_product_id(cache, product))
        if len(prices) == 0:
            return None

        prices.sort(key=lambda p: p.valid_from, reverse=False)
        oldest_price = prices[0]
        if oldest_price.valid_from > reference_date:
            # If no price is defined at the subscription start date, get the closest available price
            return oldest_price

        prices.sort(key=lambda p: p.valid_from, reverse=True)
        for price in prices:
            if price.valid_from <= reference_date:
                return price
        return None

    return get_from_cache_or_compute(price_by_date_cache, reference_date, get_price)


@transaction.atomic
def update_product(
    id_: str,
    name: str,
    base: bool,
    price: Decimal,
    size: Decimal,
    growing_period_id: str,
    description_in_bestellwizard: str,
    url_of_image_in_bestellwizard: str,
    capacity: int | None,
    min_coop_shares: int,
):
    """
    Updates a product and product price with the provided attributes.

    If the provided growing period starts in the future, the price change gets active at the start of the growing period.
    If it is the currently active growing period, the price change happens at the start of the next month.

    """
    product = Product.objects.get(id=id_)

    if base:
        Product.objects.filter(type_id=product.type.id, base=True).update(base=False)
        product.base = base

    product.name = name
    product.deleted = False
    product.description_in_bestellwizard = description_in_bestellwizard
    product.url_of_image_in_bestellwizard = url_of_image_in_bestellwizard
    product.capacity = capacity
    product.min_coop_shares = min_coop_shares
    product.save()

    price_change_date = get_next_product_price_change_date(growing_period_id)

    existing_price_change = ProductPrice.objects.filter(
        product=product, valid_from=price_change_date
    )
    if existing_price_change.exists():
        existing_price_change = existing_price_change.first()
        existing_price_change.price = price
        existing_price_change.size = size
        existing_price_change.save()
    else:
        ProductPrice.objects.create(
            price=price, product=product, size=size, valid_from=price_change_date
        )

    return product


def get_next_product_price_change_date(growing_period_id: str):
    """
    Future growing period -> price change at period.start_date
    Current growing period -> start next month

    :param growing_period_id: the growing period id
    :return: the next date on which a product price would be changed
    """

    gp = GrowingPeriod.objects.get(id=growing_period_id)
    today = get_today()

    return (
        gp.start_date
        if gp.start_date > today
        else today + relativedelta(months=1, day=1)
    )


@transaction.atomic
def delete_product(id_: str):
    """
    Deletes a product. If there are any subscriptions for the product (also historic ones), the product
    gets deleted by flag (deleted=True). Otherwise, it will be hard deleted.

    :param id_: the id of the product to delete
    """

    product = Product.objects.get(id=id_)

    if Subscription.objects.filter(product=product).exists():
        product.deleted = True
        product.save()
    else:
        ProductPrice.objects.filter(product=product).delete()
        product.delete()


@transaction.atomic
def delete_product_type_capacity(id_: str):
    """
    Deletes a product capacity by id

    :return:
    """

    pc = ProductCapacity.objects.get(id=id_)
    product_type_id = pc.product_type.id
    pc.delete()

    if not (
        ProductCapacity.objects.filter(product_type__id=product_type_id).exists()
        or Subscription.objects.filter(product__type_id=product_type_id).exists()
    ):
        ProductPrice.objects.filter(product__type__id=product_type_id).delete()
        Product.objects.filter(type__id=product_type_id).delete()
        TaxRate.objects.filter(product_type__id=product_type_id).delete()
        ProductType.objects.get(id=product_type_id).delete()


def get_smallest_product_size(
    product_type: ProductType | str, reference_date: datetime.date = None
):
    if reference_date is None:
        reference_date = get_today()

    if isinstance(product_type, ProductType):
        product_type = product_type.id

    products = Product.objects.filter(type__id=product_type)
    if not products.exists():
        raise ObjectDoesNotExist("No products found")

    all_prices = ProductPrice.objects.filter(product__type__id=product_type)
    if all_prices.count() == 1:
        return all_prices[0].size

    smallest_size = float("inf")
    for product in products:
        prices = ProductPrice.objects.filter(
            product=product, valid_from__lte=reference_date
        ).order_by("valid_from")
        if prices.count() == 0:
            continue
        smallest_size = min(smallest_size, prices.last().size)

    if smallest_size == float("inf"):
        raise ObjectDoesNotExist("No price found")

    return smallest_size


def is_product_type_available(
    product_type: ProductType | str,
    reference_date: datetime.date = None,
    cache: dict | None = None,
) -> bool:
    if reference_date is None:
        reference_date = get_today()

    if isinstance(product_type, str):
        product_type = TapirCache.get_product_type_by_id(
            cache=cache, product_type_id=product_type
        )

    if not Product.objects.filter(type=product_type, deleted=False).exists():
        return False

    from tapir.subscriptions.services.product_type_lowest_free_capacity_after_date_generic import (
        ProductTypeLowestFreeCapacityAfterDateCalculator,
    )

    free_capacity = ProductTypeLowestFreeCapacityAfterDateCalculator.get_lowest_free_capacity_after_date(
        product_type=product_type,
        reference_date=reference_date,
        cache=cache,
    )

    return free_capacity >= get_smallest_product_size(product_type, reference_date)
