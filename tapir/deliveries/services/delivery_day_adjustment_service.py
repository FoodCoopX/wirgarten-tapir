import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.models import DeliveryDayAdjustment
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import get_current_growing_period


class DeliveryDayAdjustmentService:
    @classmethod
    def get_adjusted_delivery_weekday(cls, delivery_date: datetime.date) -> int | None:
        growing_period = get_current_growing_period(delivery_date)
        if not growing_period:
            return get_parameter_value(Parameter.DELIVERY_DAY)

        delivery_week = delivery_date.isocalendar().week
        adjustment = DeliveryDayAdjustment.objects.filter(
            growing_period=growing_period, calendar_week=delivery_week
        ).first()

        if adjustment:
            return adjustment.adjusted_weekday

        return get_parameter_value(Parameter.DELIVERY_DAY)
