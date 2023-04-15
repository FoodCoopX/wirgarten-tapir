from datetime import date

from dateutil.relativedelta import relativedelta

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import WEEKLY, ODD_WEEKS, EVEN_WEEKS
from tapir.wirgarten.models import (
    PickupLocationCapability,
    PickupLocation,
    Member,
    GrowingPeriod,
    ProductType,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import (
    get_active_product_types,
    get_future_subscriptions,
)


def get_active_pickup_location_capabilities():
    return PickupLocationCapability.objects.filter(
        product_type__in=get_active_product_types()
    )


def get_active_pickup_locations(
    capabilities: [
        PickupLocationCapability
    ] = get_active_pickup_location_capabilities(),
):
    return PickupLocation.objects.filter(
        id__in=capabilities.values("pickup_location__id")
    )


def get_next_delivery_date(reference_date: date = date.today()):
    delivery_day = get_parameter_value(Parameter.DELIVERY_DAY)
    if reference_date.weekday() > delivery_day:
        next_delivery = reference_date + relativedelta(
            days=(7 - reference_date.weekday() % 7) + delivery_day
        )
    else:
        next_delivery = reference_date + relativedelta(
            days=delivery_day - reference_date.weekday()
        )
    return next_delivery


def get_next_delivery_date_for_product_type(
    product_type=ProductType, reference_date: date = date.today()
):
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


def generate_future_deliveries(member: Member):
    deliveries = []
    next_delivery_date = get_next_delivery_date()
    last_growing_period = GrowingPeriod.objects.order_by("-end_date")[:1][0]
    subs = get_future_subscriptions().filter(member=member)
    while next_delivery_date <= last_growing_period.end_date:
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
            deliveries.append(
                {
                    "delivery_date": next_delivery_date.isoformat(),
                    "pickup_location": member.pickup_location,
                    "subs": active_subs,
                }
            )

        next_delivery_date += relativedelta(days=7)

    return deliveries
