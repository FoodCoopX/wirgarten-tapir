import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.utils.shortcuts import week_to_monday
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class BreadChoiceDeadlineService:
    """
    Until when a member may still choose the bread for a delivery week.

    Enforced on the server, not only in the browser: past the deadline the
    bakery has already bought the flour and lit the oven.
    """

    @classmethod
    def get_delivery_date(
        cls, year: int, delivery_week: int, pickup_location_id, cache: dict
    ) -> datetime.date | None:
        """
        The station's own delivery date in that week.

        The station's weekday rather than the org-wide one: the bread is baked
        for when that station is served, and this is the date the member sees.
        """
        delivery_day = PickupLocationDeliveryDayService.get_delivery_day(
            pickup_location_id=pickup_location_id, cache=cache
        )
        if delivery_day is None:
            return None
        return week_to_monday(year, delivery_week) + datetime.timedelta(
            days=delivery_day
        )

    @classmethod
    def get_deadline(
        cls, year: int, delivery_week: int, pickup_location_id, cache: dict
    ) -> datetime.date | None:
        """
        The last day a change is accepted, or None when it cannot be worked out.

        Baking happens BAKERY_BAKING_DAY_BEFORE_DELIVERY_DAY before the
        delivery, and choices close
        BAKERY_LAST_CHOOSING_DAY_BEFORE_BAKING_DAY before that.
        """
        delivery_date = cls.get_delivery_date(
            year, delivery_week, pickup_location_id, cache=cache
        )
        if delivery_date is None:
            return None

        days_before_delivery = get_parameter_value(
            ParameterKeys.BAKERY_BAKING_DAY_BEFORE_DELIVERY_DAY, cache=cache
        ) + get_parameter_value(
            ParameterKeys.BAKERY_LAST_CHOOSING_DAY_BEFORE_BAKING_DAY, cache=cache
        )
        return delivery_date - datetime.timedelta(days=days_before_delivery)

    @classmethod
    def can_still_choose(
        cls, year: int, delivery_week: int, pickup_location_id, cache: dict
    ) -> bool:
        """
        A station whose delivery day is unknown has no deadline to enforce, so
        the choice stays open rather than being blocked by missing setup.
        """
        deadline = cls.get_deadline(
            year, delivery_week, pickup_location_id, cache=cache
        )
        if deadline is None:
            return True
        return get_today(cache=cache) <= deadline

    @classmethod
    def may_member_choose_breads(cls, cache: dict) -> bool:
        return bool(
            get_parameter_value(
                ParameterKeys.BAKERY_MEMBERS_CAN_CHOOSE_BREAD_SORTS, cache=cache
            )
        )
