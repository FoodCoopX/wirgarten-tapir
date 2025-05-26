import datetime
from typing import Dict

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import get_next_delivery_date


class DateLimitForDeliveryChangeCalculator:
    @classmethod
    def calculate_date_limit_for_delivery_changes_in_week(
        cls, reference_date: datetime.date, cache: Dict
    ):
        # at the latest,changes can be done at the returned date.
        # One day after the returned date, changes are not possible

        weekday_limit = get_parameter_value(
            ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL, cache=cache
        )
        weekday_delivery = get_parameter_value(ParameterKeys.DELIVERY_DAY, cache=cache)
        diff_in_days = (weekday_delivery - weekday_limit) % 7
        next_delivery_date = get_next_delivery_date(
            get_monday(reference_date), cache=cache
        )
        return next_delivery_date - datetime.timedelta(days=diff_in_days)
