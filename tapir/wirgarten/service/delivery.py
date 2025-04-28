from datetime import date
from typing import Dict

from dateutil.relativedelta import relativedelta
from typing_extensions import deprecated

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.delivery_day_adjustment_service import (
    DeliveryDayAdjustmentService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import EVEN_WEEKS, ODD_WEEKS, WEEKLY, NO_DELIVERY
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    PickupLocationCapability,
    ProductType,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import OPTIONS_WEEKDAYS
from tapir.wirgarten.service.product_standard_order import product_type_order_by
from tapir.wirgarten.service.products import (
    get_active_product_types,
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import get_today


def get_active_pickup_location_capabilities(
    reference_date: date = None, cache: Dict = None
):
    """
    Get all pickup location capabilities for active product types for the next month.
    """

    if reference_date is None:
        reference_date = get_today(cache=cache)

    next_month = reference_date + relativedelta(months=1, day=1)
    return PickupLocationCapability.objects.filter(
        product_type__in=get_active_product_types(next_month, cache=cache)
    ).order_by(*product_type_order_by("product_type__id", "product_type__name"))


def get_next_delivery_date(
    reference_date: date = None, delivery_weekday: int = None, cache: Dict = None
):
    """
    Calculates the next delivery date based on the reference date and the delivery weekday.
    """

    if reference_date is None:
        reference_date = get_today(cache=cache)

    if delivery_weekday is None:
        delivery_weekday = DeliveryDayAdjustmentService.get_adjusted_delivery_weekday(
            reference_date, cache=cache
        )

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
    product_type: ProductType, reference_date: date = None, cache: Dict = None
):
    """
    Calculates the next delivery date for a given product type based on the reference date.
    """

    if reference_date is None:
        reference_date = get_today(cache=cache)

    if product_type.delivery_cycle == NO_DELIVERY[0]:
        return reference_date

    next_delivery_date = get_next_delivery_date(reference_date, cache=cache)
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
            product_type, next_delivery_date + relativedelta(days=1), cache=cache
        )


@deprecated(
    "If possible, use tapir.deliveries.services.get_deliveries_service.GetDeliveriesService.get_deliveries instead"
)
def generate_future_deliveries(member: Member, limit: int = None, cache: Dict = None):
    """
    Generates a list of future deliveries for a given member.
    """

    deliveries = []

    last_growing_period = GrowingPeriod.objects.order_by("-end_date").first()
    if not last_growing_period:
        return deliveries

    next_delivery_date = get_next_delivery_date(cache=cache)

    subscriptions = list(
        get_active_and_future_subscriptions(cache=cache)
        .filter(member=member)
        .select_related("product__type")
    )
    while next_delivery_date <= last_growing_period.end_date and (
        limit is None or len(deliveries) < limit
    ):
        _, week_num, _ = next_delivery_date.isocalendar()
        even_week = week_num % 2 == 0

        accepted_delivery_cycles = [
            WEEKLY[0],
            EVEN_WEEKS[0] if even_week else ODD_WEEKS[0],
        ]
        active_subs = list(
            filter(
                lambda subscription: subscription.start_date <= next_delivery_date
                and (
                    subscription.end_date is None
                    or subscription.end_date <= next_delivery_date
                )
                and subscription.product.type.delivery_cycle
                in accepted_delivery_cycles,
                subscriptions,
            )
        )

        if len(active_subs) > 0:
            pickup_location_id = (
                MemberPickupLocationService.get_member_pickup_location_id_from_cache(
                    member_id=member.id, reference_date=next_delivery_date, cache=cache
                )
            )
            opening_times = TapirCache.get_opening_times_by_pickup_location_id(
                cache=cache, pickup_location_id=pickup_location_id
            )
            next_delivery_date += relativedelta(
                days=(
                    opening_times[0].day_of_week - next_delivery_date.weekday()
                    if opening_times
                    else 0
                )
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
                    "pickup_location": TapirCache.get_pickup_location_by_id(
                        cache=cache, pickup_location_id=pickup_location_id
                    ),
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
    cache: Dict = None,
):
    """
    Calculates the date at which a member pickup location changes becomes effective.
    """
    if reference_date is None:
        reference_date = get_today(cache=cache)
    if next_delivery_date is None:
        next_delivery_date = get_next_delivery_date(
            reference_date=reference_date, cache=cache
        )
    if change_until_weekday is None:
        change_until_weekday = get_parameter_value(
            ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL, cache=cache
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
