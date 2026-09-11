from tapir.utils.services.tapir_cache import TapirCache


class PickupLocationDeliveryDayService:
    """
    The weekday a pickup location is delivered on: the earliest of its opening
    days, or None when it has no opening times configured.

    Read inside loops - once per delivery when building a solver run, once per
    location when rendering the pickup list PDFs - so it is answered from one
    cached map. select_related on the location does not help, because the
    query is against PickupLocationOpeningTime.
    """

    @classmethod
    def get_delivery_day(cls, pickup_location_id, cache: dict) -> int | None:
        if pickup_location_id is None:
            return None

        return TapirCache.get_delivery_day_by_pickup_location_id(cache=cache).get(
            pickup_location_id
        )

    @classmethod
    def get_pickup_location_ids_for_delivery_day(cls, day: int, cache: dict) -> list:
        """
        Every station delivered on this weekday.

        "Delivered on" means the station's own delivery day - the earliest of
        its opening days - not merely "is open that day". A station open both
        Tuesday and Friday is delivered on Tuesday, and asking for Friday must
        not return it.
        """
        return [
            pickup_location_id
            for pickup_location_id, delivery_day in (
                TapirCache.get_delivery_day_by_pickup_location_id(cache=cache).items()
            )
            if delivery_day == day
        ]
