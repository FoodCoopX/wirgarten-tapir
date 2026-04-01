import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.parameter_keys import ParameterKeys


class DeliveryDayAdjustmentService:
    @classmethod
    def get_adjusted_delivery_weekday(
        cls, delivery_date: datetime.date, cache: dict
    ) -> int | None:
        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=delivery_date, cache=cache
        )
        if not growing_period:
            return get_parameter_value(ParameterKeys.DELIVERY_DAY, cache=cache)

        delivery_week = delivery_date.isocalendar().week

        adjustment = TapirCache.get_delivery_day_adjustment(
            growing_period_id=growing_period.id,
            calendar_week=delivery_week,
            cache=cache,
        )

        if adjustment:
            return adjustment.adjusted_weekday

        return get_parameter_value(ParameterKeys.DELIVERY_DAY, cache=cache)
