import datetime
from typing import Literal

from django.core.exceptions import ImproperlyConfigured

from tapir.utils.shortcuts import get_next_sunday
from tapir.wirgarten.models import GrowingPeriod


class SubscriptionChangeWeekToDateConverter:
    @classmethod
    def get_date_from_calendar_week(
        cls, week: int, growing_period: GrowingPeriod, boundary: Literal["start", "end"]
    ):
        year = growing_period.start_date.year

        monday = datetime.date.fromisocalendar(year=year, week=week, day=1)
        sunday = get_next_sunday(monday)
        if sunday < growing_period.start_date:
            monday = datetime.date.fromisocalendar(year=year + 1, week=week, day=1)
            sunday = get_next_sunday(monday)

        if boundary == "start":
            return max(monday, growing_period.start_date)

        if boundary == "end":
            return min(sunday, growing_period.end_date)

        raise ImproperlyConfigured(f"Unknown boundary: {boundary}")
