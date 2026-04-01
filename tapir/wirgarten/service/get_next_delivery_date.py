from datetime import date

from dateutil.relativedelta import relativedelta

from tapir.deliveries.services.delivery_day_adjustment_service import (
    DeliveryDayAdjustmentService,
)
from tapir.wirgarten.utils import get_today


def get_next_delivery_date(
    reference_date: date = None, delivery_weekday: int = None, cache: dict = None
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
