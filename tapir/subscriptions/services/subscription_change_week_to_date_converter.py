import datetime
from typing import Literal

from django.core.exceptions import ValidationError

from tapir.wirgarten.models import GrowingPeriod

Boundary = Literal["start", "end"]


class SubscriptionChangeWeekToDateConverter:
    BOUNDARIES: list[Boundary] = ["start", "end"]

    @classmethod
    def get_date_from_calendar_week(
        cls, week: int, growing_period: GrowingPeriod, boundary: Boundary
    ) -> datetime.date:
        # Returns the Monday (start) or Sunday (end) of the week, within the growing period.
        # If the week number matches twice, start dates use the first match and end dates the last one.
        weekday = 1 if boundary == "start" else 7
        start_year = growing_period.start_date.year
        years = [start_year - 1, start_year, start_year + 1]
        if boundary == "end":
            years.reverse()

        for year in years:
            try:
                date = datetime.date.fromisocalendar(year=year, week=week, day=weekday)
            except ValueError:
                continue
            if growing_period.start_date <= date <= growing_period.end_date:
                return date

        day_name = "Montag" if boundary == "start" else "Sonntag"
        raise ValidationError(
            f"Der {day_name} der KW {week} liegt nicht in der Vertragsperiode"
        )
