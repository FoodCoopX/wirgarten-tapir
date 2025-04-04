import datetime

from tapir.wirgarten.service.products import get_current_growing_period


class WeeksWithoutDeliveryService:
    @staticmethod
    def is_delivery_cancelled_this_week(delivery_date: datetime.date) -> bool:
        growing_period = get_current_growing_period(delivery_date)
        if not growing_period:
            return False

        return delivery_date.isocalendar().week in growing_period.weeks_without_delivery
