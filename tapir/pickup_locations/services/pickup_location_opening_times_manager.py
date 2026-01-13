import datetime

from tapir.wirgarten.models import PickupLocationOpeningTime


class PickupLocationOpeningTimesManager:
    @classmethod
    def update_delivery_date_to_opening_times(
        cls,
        opening_times: list[PickupLocationOpeningTime] | None,
        delivery_date: datetime.date,
    ):
        if opening_times is None or len(opening_times) == 0:
            return delivery_date

        return delivery_date + datetime.timedelta(
            days=(opening_times[0].day_of_week - delivery_date.weekday())
        )
