import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import get_next_delivery_date


class DateLimitForDeliveryChangeCalculator:
    @classmethod
    def calculate_date_limit_for_delivery_changes_in_week(
        cls, reference_date: datetime.date
    ):
        # at the latest,changes can be done at the returned date.
        # One day after the returned date, changes are not possible

        weekday_limit = get_parameter_value(
            Parameter.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL
        )
        weekday_delivery = get_parameter_value(Parameter.DELIVERY_DAY)
        diff_in_days = (weekday_delivery - weekday_limit) % 7
        next_delivery_date = get_next_delivery_date(get_monday(reference_date))
        return next_delivery_date - datetime.timedelta(days=diff_in_days)
