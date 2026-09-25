from tapir.utils.services.tapir_cache import TapirCache


class PickupLocationDeliveryDayService:
    @classmethod
    def get_delivery_day(cls, pickup_location_id, cache: dict) -> int | None:
        if pickup_location_id is None:
            return None

        return TapirCache.get_delivery_day_by_pickup_location_id(cache=cache).get(
            pickup_location_id
        )

    @classmethod
    def get_pickup_location_ids_for_delivery_day(cls, day: int, cache: dict) -> list:
        return [
            pickup_location_id
            for pickup_location_id, delivery_day in (
                TapirCache.get_delivery_day_by_pickup_location_id(cache=cache).items()
            )
            if delivery_day == day
        ]
