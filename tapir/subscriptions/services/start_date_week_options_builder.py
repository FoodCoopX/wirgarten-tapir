import datetime

from tapir.deliveries.services.delivery_date_calculator import (
    DeliveryDateCalculator,
)
from tapir.subscriptions.types import WeekOption
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import ProductType


class StartDateWeekOptionsBuilder:
    @classmethod
    def build_week_options(
        cls,
        product_type: ProductType,
        first_date: datetime.date,
        last_date: datetime.date,
        next_possible_start: datetime.date,
        cache: dict,
    ) -> list[WeekOption]:
        monday = get_monday(first_date)
        if monday < first_date:
            monday += datetime.timedelta(weeks=1)

        week_options = []
        while monday <= last_date:
            week_options.append(
                WeekOption(
                    date=monday,
                    is_before_next_possible_start=monday < next_possible_start,
                    has_no_delivery=product_type.delivery_cycle != NO_DELIVERY[0]
                    and not DeliveryDateCalculator.is_week_delivered(
                        product_type=product_type,
                        delivery_date=monday,
                        check_for_weeks_without_delivery=True,
                        cache=cache,
                    ),
                )
            )
            monday += datetime.timedelta(weeks=1)
        return week_options
