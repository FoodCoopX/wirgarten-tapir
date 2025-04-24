import datetime
from typing import Dict

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.models import DeliveryDayAdjustment
from tapir.utils.shortcuts import get_from_cache_or_compute
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_current_growing_period


class DeliveryDayAdjustmentService:
    @classmethod
    def get_adjusted_delivery_weekday(
        cls, delivery_date: datetime.date, cache: Dict
    ) -> int | None:
        growing_period = get_current_growing_period(delivery_date, cache=cache)
        if not growing_period:
            return get_parameter_value(ParameterKeys.DELIVERY_DAY, cache=cache)

        delivery_week = delivery_date.isocalendar().week

        delivery_adjustment_by_growing_period_cache = get_from_cache_or_compute(
            cache, "delivery_adjustments_by_growing_period", lambda: {}
        )
        delivery_adjustment_by_calendar_week = get_from_cache_or_compute(
            delivery_adjustment_by_growing_period_cache, growing_period, lambda: {}
        )
        adjustment = get_from_cache_or_compute(
            delivery_adjustment_by_calendar_week,
            delivery_week,
            lambda: DeliveryDayAdjustment.objects.filter(
                growing_period=growing_period, calendar_week=delivery_week
            ).first(),
        )

        if adjustment:
            return adjustment.adjusted_weekday

        return get_parameter_value(ParameterKeys.DELIVERY_DAY, cache=cache)
