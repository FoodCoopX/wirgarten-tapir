import datetime

from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import (
    EVERY_FOUR_WEEKS,
    NO_DELIVERY,
    WEEKLY,
    EVEN_WEEKS,
    ODD_WEEKS,
    CUSTOM_CYCLE,
)
from tapir.wirgarten.models import ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys


class DeliveryCycleService:
    @classmethod
    def is_product_type_delivered_in_week(
        cls, product_type: ProductType, date: datetime.date, cache: dict
    ) -> bool:
        cycle = product_type.delivery_cycle

        if cycle == NO_DELIVERY[0]:
            return False
        if cycle == WEEKLY[0]:
            return True
        if cycle == EVERY_FOUR_WEEKS[0]:
            return cls.is_week_delivered_in_four_week_rhythm(date=date, cache=cache)
        if cycle == CUSTOM_CYCLE[0]:
            return cls.is_week_delivered_in_custom_cycle(
                date=date, product_type=product_type, cache=cache
            )

        _, week_num, _ = date.isocalendar()
        even_week = week_num % 2 == 0

        if cycle == EVEN_WEEKS[0]:
            return even_week
        if cycle == ODD_WEEKS[0]:
            return not even_week

        raise ImproperlyConfigured(f"Unknown delivery cycle: {cycle}")

    @classmethod
    def is_week_delivered_in_custom_cycle(
        cls, date: datetime.date, product_type: ProductType, cache: dict
    ):
        week_of_potential_delivery = date.isocalendar().week

        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=date, cache=cache
        )
        delivered_weeks = TapirCache.get_delivered_weeks_for_custom_cycle(
            product_type=product_type, growing_period=growing_period, cache=cache
        )

        return week_of_potential_delivery in delivered_weeks

    @classmethod
    def is_week_delivered_in_four_week_rhythm(
        cls, date: datetime.date, cache: dict
    ) -> bool:
        start_point = get_parameter_value(
            ParameterKeys.SUBSCRIPTION_FOUR_WEEK_CYCLE_START_POINT, cache=cache
        )

        start_point = get_monday(start_point)
        date = get_monday(date)

        return ((start_point - date).days / 7) % 4 == 0
