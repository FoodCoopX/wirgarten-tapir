from datetime import date
from decimal import Decimal
from typing import List

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.db.models import Case, IntegerField, Value, When

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import ProductTypes
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
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.utils import get_today
from tapir.wirgarten.validators import (
    validate_date_range,
    validate_growing_period_overlap,
)


def get_total_price_for_subs(subs: List[Payable]) -> float:
    """
    Returns the total amount of one payment for the given list of subs.

    :param subs: the list of subs (e.g. that are currently active for a user)
    :return: the total price in €
    """
    return round(sum([x.total_price() for x in subs]), 2)


def product_type_order_by(id_field: str = "id", name_field: str = "name"):
    """
    The result of the function is meant to be passed to the order_by clause of QuerySets referencing (directly or indirectly) product types.
    The base product type which is configured via parameter is the first result. In case the parameter is not there, only the name field will be used to order.

    It is basically a workaround to use this order by condition in a static way although it depends on the parameter to be there.

    :param id_field: name/path of the "id" field. E.g. "product_type__id"
    :param name_field: name/path of the "name" field. E.g. "product_type__name"
    :return: an array of order conditions
    """

    try:
        return [
            Case(
                When(
                    **{id_field: get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)},
                    then=Value(0),
                ),
                default=1,
                output_field=IntegerField(),
            ),
            name_field,
        ]
    except BaseException:
        return [name_field]


def get_active_product_types(reference_date: date = None) -> iter:
    """
    Returns the product types which are active for the given reference date.

    :param reference_date: default: today()
    :return: the QuerySet of ProductTypes filtered for the given reference date
    """
    if reference_date is None:
        reference_date = get_today()

    return ProductType.objects.filter(
        id__in=ProductCapacity.objects.filter(
            period__start_date__lte=reference_date, period__end_date__gte=reference_date
        ).values("product_type__id")
    ).order_by(*product_type_order_by())


def get_available_product_types(reference_date: date = None) -> iter:
    if reference_date is None:
        reference_date = get_today()

    product_types = get_active_product_types(reference_date)
    return [p for p in product_types if is_product_type_available(p, reference_date)]


def get_next_growing_period(
    reference_date: date = None,
) -> GrowingPeriod | None:
    if reference_date is None:
        reference_date = get_today()

    try:
        return (
            GrowingPeriod.objects.filter(start_date__gt=reference_date)
            .order_by("start_date")
            .first()
        )
    except GrowingPeriod.DoesNotExist:
        return None


def get_current_growing_period(
    reference_date: date = None,
) -> GrowingPeriod | None:
    if reference_date is None:
        reference_date = get_today()

    try:
        return (
            GrowingPeriod.objects.filter(
                start_date__lte=reference_date, end_date__gte=reference_date
            )
            .order_by("start_date")
            .first()
        )
    except GrowingPeriod.DoesNotExist:
        return None


@transaction.atomic
def create_growing_period(start_date: date, end_date: date) -> GrowingPeriod:
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
    )


@transaction.atomic
def copy_growing_period(growing_period_id: str, start_date: date, end_date: date):
    """
    Creates a new growing period and copies all product capacities from the given growing period.

    :param growing_period_id: the original growing period id
    :param start_date: the start of the new growing period
    :param end_date: the end of the new growing period
    """

    new_growing_period = create_growing_period(start_date=start_date, end_date=end_date)
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


def get_active_product_capacities(reference_date: date = None):
    """
    Gets the active product capacities for the given reference date.

    :param reference_date: the date on which the capacity must be active
    :return: queryset of active product capacities
    """
    if reference_date is None:
        reference_date = get_today()

    return ProductCapacity.objects.filter(
        period__start_date__lte=reference_date, period__end_date__gte=reference_date
    ).order_by(*product_type_order_by("product_type_id", "product_type__name"))


def get_future_subscriptions(reference_date: date = None):
    """
    Gets active and future subscriptions. Future means e.g.: user just signed up and the contract starts next month

    :param reference_date: the date on which the capacity must be active
    :return: queryset of active and future subscriptions
    """
    if reference_date == None:
        reference_date = get_today()

    return Subscription.objects.filter(end_date__gte=reference_date).order_by(
        *product_type_order_by("product__type_id", "product__type__name")
    )


def get_active_subscriptions(reference_date: date = None):
    """
    Gets currently active subscriptions. Subscriptions that are ordered but starting next month are not included!

    :param reference_date: the date on which the subscription must be active
    :return: queryset of active subscription
    """
    if reference_date is None:
        reference_date = get_today()

    return get_future_subscriptions(reference_date).filter(
        start_date__lte=reference_date
    )


@transaction.atomic
def create_product(name: str, price: Decimal, capacity_id: str, base=False):
    """
    Creates a product and product price with the given attributes.

    :param name: the name of the product
    :param price: the price
    :param capacity_id: gets information about the growing period and product type via the capacity
    :return: the newly created product
    """
    pc = ProductCapacity.objects.get(id=capacity_id)

    product = Product.objects.create(name=name, type_id=pc.product_type.id, base=base)

    ProductPrice.objects.create(
        price=price,
        product=product,
        valid_from=get_next_product_price_change_date(growing_period_id=pc.period.id),
    )

    return product


def get_product_price(product: Product, reference_date: date = None):
    """
    Returns the currently active product price.

    :param product: the product
    :param reference_date: reference date for when the price should be valid
    :return: the ProductPrice instance
    """
    if reference_date is None:
        reference_date = get_today()

    prices = ProductPrice.objects.filter(product=product).order_by("-valid_from")

    # If there's only one price, return it
    if prices.count() == 1:
        return prices.first()
    else:  # Otherwise, return the price valid up to the reference date
        return prices.filter(valid_from__lte=reference_date).first()


@transaction.atomic
def update_product(id_: str, name: str, price: Decimal, growing_period_id: str):
    """
    Updates a product and product price with the provided attributes.

    If the provided growing period starts in the future, the price change gets active at the start of the growing period.
    If it is the currently active growing period, the price change happens at the start of the next month.

    :param id_: the id of the product to update
    :param name: the name of the product
    :param price: the price of the product
    :param growing_period_id: the growing period id
    :return:
    """

    product = Product.objects.get(id=id_)
    product.name = name
    product.deleted = False
    product.save()

    price_change_date = get_next_product_price_change_date(growing_period_id)

    existing_price_change = ProductPrice.objects.filter(
        product=product, valid_from=price_change_date
    )
    if existing_price_change.exists():
        existing_price_change = existing_price_change.first()
        existing_price_change.price = price
        existing_price_change.save()
    else:
        ProductPrice.objects.create(
            price=price, product=product, valid_from=price_change_date
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
    gets deleted by flag (deleted=True). Otherwise it will be hard deleted.

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
def create_product_type_capacity(
    name: str,
    contract_link: str,
    icon_link: str,
    single_subscription_only: bool,
    delivery_cycle: str,
    default_tax_rate: float,
    capacity: Decimal,
    period_id: str,
    product_type_id: str = "",
):
    """
    Creates or updates the product type and creates the capacity and default tax rate for the given period.

    :param name: the name of the product type
    :param delivery_cycle: the delivery cycle of the product type
    :param default_tax_rate: the default tax rate percent
    :param capacity: the capacity of this product type for the given growing period
    :param period_id: the id of the growing period
    :param product_type_id: if set, the product type is updated, else a new product type is created
    :return: the newly created product capacity
    """

    # update or create product type
    if product_type_id is not None and len(product_type_id.strip()) > 0:
        pt = ProductType.objects.get(id=product_type_id)
        pt.delivery_cycle = delivery_cycle
        pt.contract_link = contract_link
        pt.icon_link = icon_link
        pt.single_subscription_only = single_subscription_only
        pt.save()
    else:
        pt = ProductType.objects.create(
            name=name,
            delivery_cycle=delivery_cycle,
            contract_link=contract_link,
            icon_link=icon_link,
            single_subscription_only=single_subscription_only,
        )
        if not ProductType.objects.exists():
            Parameter.objects.filter(name=Parameter.COOP_BASE_PRODUCT_TYPE).update(
                value=pt.id
            )

    # tax rate
    period = GrowingPeriod.objects.get(id=period_id)
    today = get_today()
    create_or_update_default_tax_rate(
        product_type_id=pt.id,
        tax_rate=default_tax_rate,
        tax_rate_change_date=today if period.start_date < today else period.start_date,
    )

    # capacity
    return ProductCapacity.objects.create(
        period_id=period_id,
        product_type=pt,
        capacity=capacity,
    )


@transaction.atomic
def update_product_type_capacity(
    id_: str,
    name: str,
    contract_link: str,
    icon_link: str,
    single_subscription_only: bool,
    delivery_cycle: str,
    default_tax_rate: float,
    capacity: Decimal,
    tax_rate_change_date: date,
):
    """
    Updates the product type and the capacity for the given period.

    :param id_: the id of the product capacity to update
    :param name: the new name of the product type
    :param delivery_cycle: the new delivery cycle of the product type
    :param default_tax_rate: the new default tax rate percent
    :param capacity: the new capacity in EUR
    :param tax_rate_change_date: the date at which the new default tax rate becomes active
    """

    # capacity
    cp = ProductCapacity.objects.get(id=id_)
    cp.capacity = capacity
    cp.save()

    cp.product_type.name = name
    cp.product_type.contract_link = contract_link
    cp.product_type.icon_link = icon_link
    cp.product_type.single_subscription_only = single_subscription_only
    cp.product_type.delivery_cycle = delivery_cycle
    cp.product_type.save()

    # tax rate
    create_or_update_default_tax_rate(
        product_type_id=cp.product_type.id,
        tax_rate=default_tax_rate,
        tax_rate_change_date=tax_rate_change_date,
    )


@transaction.atomic
def delete_product_type_capacity(id_: str):
    """
    Deletes a product capacity by

    :param period_id:
    :param product_type_id:
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


@transaction.atomic
def create_or_update_default_tax_rate(
    product_type_id: str, tax_rate: float, tax_rate_change_date: date
):
    """
    Updates the default tax rate for the given product type id.

    If a default tax rate already exists, set the end date to end of the month and create a new default tax rate for next month.
    Otherwise, just create a tax rate valid from today.

    :param product_type_id:
    :param tax_rate:
    :return:
    """

    try:
        tr = TaxRate.objects.get(product_type__id=product_type_id, valid_to=None)
        if tr.tax_rate != tax_rate:
            tr.valid_to = tax_rate_change_date + relativedelta(days=-1)
            tr.save()

            TaxRate.objects.create(
                product_type_id=product_type_id,
                tax_rate=tax_rate,
                valid_from=tax_rate_change_date,
                valid_to=None,
            )
    except TaxRate.DoesNotExist:
        TaxRate.objects.create(
            product_type_id=product_type_id,
            tax_rate=tax_rate,
            valid_from=get_today(),
            valid_to=None,
        )


def get_free_product_capacity(product_type_id: str, reference_date: date = None):
    if reference_date == None:
        reference_date = get_today()

    active_product_capacities = get_active_product_capacities(reference_date).filter(
        product_type_id=product_type_id
    )
    if active_product_capacities.exists():
        total_capacity = float(active_product_capacities.first().capacity)
        used_capacity = sum(
            map(
                lambda sub: float(get_product_price(sub.product, reference_date).price)
                * sub.quantity,
                get_future_subscriptions(reference_date).filter(
                    product__type_id=product_type_id
                ),
            )
        )
        return total_capacity - used_capacity
    else:
        return 0


def get_cheapest_product_price(
    product_type: ProductType | str, reference_date: date = None
):
    if reference_date == None:
        reference_date = get_today()

    if type(product_type) == ProductType:
        product_type = product_type.id

    product_prices = ProductPrice.objects.filter(product__type_id=product_type)
    if len(product_prices) > 1:
        product_prices.filter(valid_from__lte=reference_date).order_by("price")

    return product_prices.first().price


def is_product_type_available(
    product_type: ProductType | str, reference_date: date = None
) -> bool:
    if reference_date == None:
        reference_date = get_today()

    if type(product_type) == ProductType:
        product_type = product_type.id

    return get_free_product_capacity(
        product_type_id=product_type, reference_date=reference_date
    ) > get_cheapest_product_price(product_type, reference_date)
