import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.models import Joker
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import get_next_delivery_date
from tapir.wirgarten.service.products import get_current_growing_period
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
    def can_joker_be_used_relative_to_date_limit(
        cls, reference_date: datetime.date
    ) -> bool:
        return cls.get_date_limit_for_joker_changes(reference_date) > get_today()

    @classmethod
    def can_joker_be_used_relative_to_max_amount_per_growing_period(
        cls, member: Member, reference_date: datetime.date
    ) -> bool:
        growing_period = get_current_growing_period(reference_date)
        if not growing_period:
            return False

        nb_used_jokers_in_growing_period = Joker.objects.filter(
            member=member,
            date__gte=growing_period.start_date,
            date__lte=growing_period.end_date,
        ).count()

        return nb_used_jokers_in_growing_period < get_parameter_value(
            Parameter.JOKERS_AMOUNT_PER_CONTRACT
        )

    @classmethod
    def can_joker_be_cancelled(cls, joker: Joker) -> bool:
        return get_today() <= cls.get_date_limit_for_joker_changes(joker.date)

    @classmethod
    def cancel_joker(cls, joker: Joker):
        joker.delete()
