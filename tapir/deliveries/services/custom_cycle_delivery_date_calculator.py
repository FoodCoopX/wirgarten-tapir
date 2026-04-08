import datetime

from tapir.deliveries.exceptions import TapirCustomCycleException
from tapir.deliveries.models import CustomCycleScheduledDeliveryWeek
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_next_sunday
from tapir.wirgarten.models import GrowingPeriod, ProductType
from tapir.wirgarten.utils import format_date


class CustomCycleDeliveryDateCalculator:
    @classmethod
    def does_product_type_have_at_least_one_delivery_in_the_future(
        cls, product_type: ProductType, reference_date: datetime.date, cache: dict
    ):
        scheduled_weeks = TapirCache.get_all_scheduled_weeks_for_custom_cycle(
            product_type=product_type, cache=cache
        )
        for scheduled_week in scheduled_weeks:
            if (
                CustomCycleDeliveryDateCalculator.get_date_from_scheduled_week(
                    scheduled_week=scheduled_week
                )
                >= reference_date
            ):
                return True

        return False

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
                f"Die ganze Woche muss innerhalb der Vertragsperiode liegen. KW{week} geht von {format_date(monday)} zu {format_date(sunday)}"
            )

        return monday
