import datetime
from typing import Dict

from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import (
    EVERY_FOUR_WEEKS,
    NO_DELIVERY,
    WEEKLY,
    EVEN_WEEKS,
    ODD_WEEKS,
    DeliveryCycle,
)
from tapir.wirgarten.parameter_keys import ParameterKeys


class DeliveryCycleService:
    @classmethod
    def is_cycle_delivered_in_week(
        cls, cycle: str, date: datetime.date, cache: Dict
    ) -> bool:
        if cycle == NO_DELIVERY[0]:
            return False
        if cycle == WEEKLY[0]:
            return True
        if cycle == EVERY_FOUR_WEEKS[0]:
            return cls.is_week_delivered_in_four_week_rhythm(date=date, cache=cache)

        _, week_num, _ = date.isocalendar()
        even_week = week_num % 2 == 0

        if cycle == EVEN_WEEKS[0]:
            return even_week
        if cycle == ODD_WEEKS[0]:
            return not even_week

        raise ImproperlyConfigured(f"Unknown delivery cycle: {cycle}")

    @classmethod
    def is_week_delivered_in_four_week_rhythm(
        cls, date: datetime.date, cache: Dict
    ) -> bool:
        start_point = get_parameter_value(
            ParameterKeys.SUBSCRIPTION_FOUR_WEEK_CYCLE_START_POINT, cache=cache
        )

        start_point = get_monday(start_point)
        date = get_monday(date)

        return ((start_point - date).days / 7) % 4 == 0

    @classmethod
    def get_cycles_delivered_in_week(cls, date: datetime.date, cache: Dict):
        return [
            cycle[0]
            for cycle in DeliveryCycle
            if DeliveryCycleService.is_cycle_delivered_in_week(
                cycle=cycle[0], date=date, cache=cache
            )
        ]
