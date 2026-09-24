from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import OPTIONS_WEEKDAYS


class PickupLocationOpeningTimesFormatter:
    @classmethod
    def get_formatted_opening_times(cls, pickup_location_id: str, cache: dict):
        formatted_times = []
        for opening_time in TapirCache.get_opening_times_by_pickup_location_id(
            pickup_location_id=pickup_location_id, cache=cache
        ):
            open_time = opening_time.open_time.strftime("%H:%M")
            close_time = opening_time.close_time.strftime("%H:%M")

            formatted_times.append(
                f"{OPTIONS_WEEKDAYS[opening_time.day_of_week][1]}: {open_time}-{close_time}"
            )
        return ", ".join(formatted_times)
