from datetime import date
from typing import List

from dateutil.relativedelta import relativedelta

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import EVEN_WEEKS, ODD_WEEKS, WEEKLY
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    PickupLocation,
    PickupLocationCapability,
    PickupLocationOpeningTime,
    ProductType,
)
from tapir.wirgarten.parameters import OPTIONS_WEEKDAYS, Parameter
from tapir.wirgarten.service.products import (
    get_active_product_types,
    get_future_subscriptions,
)
from tapir.wirgarten.utils import get_today


def get_active_pickup_location_capabilities(reference_date: date = None):
    if reference_date is None:
        reference_date = get_today()

    return PickupLocationCapability.objects.filter(
        product_type__in=get_active_product_types(reference_date=reference_date)
    )


def get_active_pickup_locations(
    capabilities: List[PickupLocationCapability] = None,
):
    if capabilities is None:
        get_active_pickup_location_capabilities()

    return PickupLocation.objects.filter(
        id__in=capabilities.values("pickup_location__id")
    )


def get_next_delivery_date(reference_date: date = None, delivery_weekday: int = None):
    if reference_date is None:
        reference_date = get_today()

    if delivery_weekday is None:
        delivery_weekday = get_parameter_value(Parameter.DELIVERY_DAY)

    if reference_date.weekday() > delivery_weekday:
        next_delivery = reference_date + relativedelta(
            days=(7 - reference_date.weekday() % 7) + delivery_weekday
        )
    else:
        next_delivery = reference_date + relativedelta(
            days=delivery_weekday - reference_date.weekday()
        )
    return next_delivery


def get_next_delivery_date_for_product_type(
    product_type: ProductType, reference_date: date = None
):
    if reference_date is None:
        reference_date = get_today()

    next_delivery_date = get_next_delivery_date(reference_date)
    _, week_num, _ = next_delivery_date.isocalendar()
    even_week = week_num % 2 == 0

    if (
        product_type.delivery_cycle == WEEKLY[0]
        or (even_week and product_type.delivery_cycle == EVEN_WEEKS[0])
        or ((not even_week) and product_type.delivery_cycle == ODD_WEEKS[0])
    ):
        return next_delivery_date
    else:
        return get_next_delivery_date_for_product_type(
            product_type, next_delivery_date + relativedelta(days=1)
        )


def generate_future_deliveries(member: Member, limit: int = None):
    deliveries = []
    next_delivery_date = get_next_delivery_date()
    last_growing_period = GrowingPeriod.objects.order_by("-end_date")[:1][0]
    subs = get_future_subscriptions().filter(member=member)
    while next_delivery_date <= last_growing_period.end_date and (
        limit is None or len(deliveries) < limit
    ):
        _, week_num, _ = next_delivery_date.isocalendar()
        even_week = week_num % 2 == 0

        active_subs = subs.filter(
            start_date__lte=next_delivery_date,
            end_date__gte=next_delivery_date,
            product__type__delivery_cycle__in=[
                WEEKLY[0],
                EVEN_WEEKS[0] if even_week else ODD_WEEKS[0],
            ],
        )

        if active_subs.count() > 0:
            pickup_location = member.get_pickup_location(next_delivery_date)
            opening_times = PickupLocationOpeningTime.objects.filter(
                pickup_location=pickup_location
            )
            next_delivery_date += relativedelta(
                days=opening_times[0].day_of_week - next_delivery_date.weekday()
                if opening_times
                else 0
            )

            opening_times = enumerate(
                map(
                    lambda x: {
                        "day_of_week": OPTIONS_WEEKDAYS[x.day_of_week][1],
                        "open_time": x.open_time,
                        "close_time": x.close_time,
                    },
                    opening_times,
                )
            )

            deliveries.append(
                {
                    "delivery_date": next_delivery_date.isoformat(),
                    "pickup_location": pickup_location,
                    "subs": active_subs,
                    "opening_times": opening_times,
                }
            )

        next_delivery_date += relativedelta(days=7)

    return deliveries


def calculate_pickup_location_change_date(
    reference_date=None,
    next_delivery_date=None,
    change_until_weekday=None,
):
    """
    Calculates the date at which a member pickup location changes becomes effective.
    """
    if reference_date is None:
        reference_date = get_today()
    if next_delivery_date is None:
        next_delivery_date = get_next_delivery_date()
    if change_until_weekday is None:
        change_until_weekday = get_parameter_value(
            Parameter.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL
        )

    days_ahead = next_delivery_date.weekday() - change_until_weekday
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    change_until_date = next_delivery_date - relativedelta(days=days_ahead)

    # If today is the same as next_delivery
    if reference_date == next_delivery_date:
        return next_delivery_date + relativedelta(days=1)

    # Otherwise, if today <= change_until_date, change happens today
    elif reference_date <= change_until_date:
        return reference_date

    # If today > change_until_date, change happens after next_delivery
    else:
        return next_delivery_date + relativedelta(days=1)
