import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class ContractStartDateCalculator:
    @classmethod
    def get_next_contract_start_date(cls, reference_date: datetime.date, cache: dict):
        """
        Gets the earliest possible start date for a contract
        """
        current_date = get_monday(reference_date)

        while not cls.can_contract_start_on_date(
            reference_date=current_date, cache=cache
        ):
            current_date += datetime.timedelta(weeks=1)
        return current_date

    @classmethod
    def can_contract_start_on_date(
        cls, reference_date: datetime.date, cache: dict
    ) -> bool:
        date_limit = DateLimitForDeliveryChangeCalculator.calculate_date_limit_for_delivery_changes_in_week(
            reference_date=reference_date, cache=cache
        )
        date_limit -= datetime.timedelta(
            days=get_parameter_value(
                key=ParameterKeys.SUBSCRIPTION_BUFFER_TIME_BEFORE_START, cache=cache
            )
        )
        return date_limit >= get_today(cache=cache)
