from datetime import date

from django.db import transaction

from tapir.wirgarten.models import (
    Subscription,
    ProductCapacity,
    GrowingPeriod,
    ProductType,
    Payable,
)
from tapir.wirgarten.validators import (
    validate_growing_period_overlap,
    validate_date_range,
)


def get_total_price_for_subs(subs: [Payable]) -> float:
    """
    Returns the total amount of one payment for the given list of subs.

    :param subs: the list of subs (e.g. that are currently active for a user)
    :return: the total price in €
    """
    return round(
        sum(
            map(
                lambda x: x.get_total_price(),
                subs,
            )
        ),
        2,
    )


def get_active_product_types(reference_date: date = date.today()) -> iter:
    """
    Returns the product types which are active for the given reference date.

    :param reference_date: default: today()
    :return: the QuerySet of ProductTypes filtered for the given reference date
    """

    return ProductType.objects.filter(
        id__in=ProductCapacity.objects.filter(
            period__start_date__lte=reference_date, period__end_date__gte=reference_date
        ).values("product_type__id")
    )


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


def get_active_product_capacities(reference_date: date = date.today()):
    """
    Gets the active product capacities for the given reference date.

    :param reference_date: the date on which the capacity must be active
    :return: queryset of active product capacities
    """
    return ProductCapacity.objects.filter(
        period__start_date__lte=reference_date, period__end_date__gte=reference_date
    )


def get_future_subscriptions(reference_date: date = date.today()):
    """
    Gets active and future subscriptions. Future means e.g.: user just signed up and the contract starts next month

    :param reference_date: the date on which the capacity must be active
    :return: queryset of active and future subscriptions
    """
    return Subscription.objects.filter(end_date__gte=reference_date)


def get_active_subscriptions(reference_date: date = date.today()):
    """
    Gets currently active subscriptions. Subscriptions that are ordered but starting next month are not included!

    :param reference_date: the date on which the subscription must be active
    :return: queryset of active subscription
    """
    return get_future_subscriptions().filter(start_date__lte=reference_date)
