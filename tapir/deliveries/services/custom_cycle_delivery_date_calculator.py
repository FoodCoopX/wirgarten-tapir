import datetime

from tapir.deliveries.models import CustomCycleDeliveryWeeks
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import GrowingPeriod, ProductType


class CustomCycleDeliveryDateCalculator:
    @classmethod
    def does_product_type_have_at_least_one_delivery_in_the_future(
        cls, product_type: ProductType, reference_date: datetime.date, cache: dict
    ):
        week_objects = TapirCache.get_all_delivered_week_objects_for_custom_cycle(
            product_type=product_type, cache=cache
        )
        for week_object in week_objects:
            if (
                CustomCycleDeliveryDateCalculator.get_date_from_week_object(
                    week_object=week_object
                )
                >= reference_date
            ):
                return True

        return False

    @classmethod
    def get_date_from_week_object(cls, week_object: CustomCycleDeliveryWeeks):
        return cls.get_date_from_calendar_week(
            week=week_object.calendar_week, growing_period=week_object.growing_period
        )

    @classmethod
    def get_date_from_calendar_week(cls, week: int, growing_period: GrowingPeriod):
        year = growing_period.start_date.year
        date = datetime.date.fromisocalendar(year=year, week=week, day=1)

        if date < growing_period.start_date:
            date = datetime.date.fromisocalendar(year=year + 1, week=week, day=1)

        return date
