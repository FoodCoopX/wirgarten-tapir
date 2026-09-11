import datetime

from tapir.deliveries.exceptions import TapirCustomCycleException
from tapir.deliveries.models import CustomCycleScheduledDeliveryWeek
from tapir.utils.shortcuts import get_next_sunday
from tapir.wirgarten.models import GrowingPeriod
from tapir.wirgarten.utils import format_date


class CustomCycleDeliveryDateCalculator:
    @classmethod
    def get_date_from_scheduled_week(
        cls, scheduled_week: CustomCycleScheduledDeliveryWeek
    ):
        return cls.get_date_from_calendar_week(
            week=scheduled_week.calendar_week,
            growing_period=scheduled_week.growing_period,
        )

    @classmethod
    def get_date_from_calendar_week(cls, week: int, growing_period: GrowingPeriod):
        year = growing_period.start_date.year
        monday = datetime.date.fromisocalendar(year=year, week=week, day=1)
        sunday = get_next_sunday(monday)
        if sunday < growing_period.start_date:
            monday = datetime.date.fromisocalendar(year=year + 1, week=week, day=1)
            sunday = get_next_sunday(monday)

        if (
            monday < growing_period.start_date
            or monday > growing_period.end_date
            or sunday < growing_period.start_date
            or sunday > growing_period.end_date
        ):
            raise TapirCustomCycleException(
                f"Die ganze Woche muss innerhalb der Vertragsperiode liegen. KW{week} geht vom {format_date(monday)} bis zum {format_date(sunday)}"
            )

        return monday
