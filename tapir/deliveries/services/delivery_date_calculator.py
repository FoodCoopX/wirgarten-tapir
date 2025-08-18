import datetime

from tapir.deliveries.services.delivery_cycle_service import DeliveryCycleService
from tapir.deliveries.services.get_deliveries_service import GetDeliveriesService
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import NO_DELIVERY


class DeliveryDateCalculator:
    @classmethod
    def get_next_delivery_date_any_product(
        cls, reference_date: datetime.date, pickup_location_id, cache: dict
    ):
        opening_times = TapirCache.get_opening_times_by_pickup_location_id(
            cache=cache, pickup_location_id=pickup_location_id
        )

        delivery_date_this_week = (
            GetDeliveriesService.update_delivery_date_to_opening_times(
                opening_times=opening_times, delivery_date=reference_date
            )
        )
        if delivery_date_this_week > reference_date:
            return delivery_date_this_week

        delivery_date_next_week = (
            GetDeliveriesService.update_delivery_date_to_opening_times(
                opening_times=opening_times,
                delivery_date=reference_date + datetime.timedelta(days=7),
            )
        )
        return delivery_date_next_week

    @classmethod
    def get_next_delivery_date_for_delivery_cycle(
        cls,
        reference_date: datetime.date,
        pickup_location_id,
        delivery_cycle: str,
        cache: dict,
    ):
        delivery_date = cls.get_next_delivery_date_any_product(
            reference_date=reference_date,
            pickup_location_id=pickup_location_id,
            cache=cache,
        )
        if delivery_cycle == NO_DELIVERY[0]:
            return delivery_date

        while not DeliveryCycleService.is_cycle_delivered_in_week(
            delivery_cycle, date=delivery_date, cache=cache
        ):
            delivery_date = cls.get_next_delivery_date_any_product(
                reference_date=delivery_date + datetime.timedelta(days=1),
                pickup_location_id=pickup_location_id,
                cache=cache,
            )

        return delivery_date
