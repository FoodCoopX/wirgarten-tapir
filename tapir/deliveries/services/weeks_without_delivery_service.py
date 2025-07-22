import datetime
from typing import Dict

from tapir.utils.services.tapir_cache import TapirCache


class WeeksWithoutDeliveryService:
    @staticmethod
    def is_delivery_cancelled_this_week(
        delivery_date: datetime.date, cache: Dict
    ) -> bool:
        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=delivery_date, cache=cache
        )
        if not growing_period:
            return False

        return delivery_date.isocalendar().week in growing_period.weeks_without_delivery
