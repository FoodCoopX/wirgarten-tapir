import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.delivery_day_adjustment_service import (
    DeliveryDayAdjustmentService,
)
from tapir.pickup_locations.services.pickup_location_opening_times_manager import (
    PickupLocationOpeningTimesManager,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.parameter_keys import ParameterKeys


class PickupLocationDeliveryDateCalculator:
    @classmethod
    def get_delivery_date_at_pickup_location(
        cls,
        pickup_location_id: str | None,
        delivery_date: datetime.date,
        cache: dict,
    ) -> datetime.date:
        opening_times = None
        if pickup_location_id is not None:
            opening_times = TapirCache.get_opening_times_by_pickup_location_id(
                cache=cache, pickup_location_id=pickup_location_id
            )
        delivery_date = (
            PickupLocationOpeningTimesManager.update_delivery_date_to_opening_times(
                opening_times=opening_times, delivery_date=delivery_date
            )
        )
        adjusted_weekday = DeliveryDayAdjustmentService.get_adjusted_delivery_weekday(
            delivery_date=delivery_date, cache=cache
        )
        if adjusted_weekday != get_parameter_value(
            key=ParameterKeys.DELIVERY_DAY, cache=cache
        ):
            delivery_date = get_monday(delivery_date) + datetime.timedelta(
                days=adjusted_weekday
            )

        return delivery_date
