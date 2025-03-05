import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.models import Joker
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.utils import get_today


class JokerManagementService:
    @classmethod
    def get_date_limit_for_joker_changes(cls, reference_date: datetime.date):
        # at the latest, jokers can be used or cancelled at the returned date.
        # One day after the returned date, they cannot be changed anymore

        weekday_limit = get_parameter_value(
            Parameter.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL
        )
        weekday_delivery = get_parameter_value(Parameter.DELIVERY_DAY)
        diff_in_days = (weekday_delivery - weekday_limit) % 7
        next_delivery_date = get_next_delivery_date(get_monday(reference_date))
        return next_delivery_date - datetime.timedelta(days=diff_in_days)

    @classmethod
    def can_joker_be_used(cls, reference_date: datetime.date) -> bool:
        return cls.get_date_limit_for_joker_changes(reference_date) > get_today()

    @classmethod
    def can_joker_be_cancelled(cls, joker: Joker) -> bool:
        return get_today() <= cls.get_date_limit_for_joker_changes(joker.date)

    @classmethod
    def cancel_joker(cls, joker: Joker):
        joker.delete()
