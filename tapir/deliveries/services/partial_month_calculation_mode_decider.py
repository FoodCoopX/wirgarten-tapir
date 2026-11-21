import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class PartialMonthCalculationModeDecider:
    @classmethod
    def is_proportional_mode_active(
        cls, first_of_month: datetime.date, cache: dict
    ) -> bool:
        return first_of_month >= get_parameter_value(
            ParameterKeys.PAYMENT_PARTIAL_MONTH_PROPORTIONAL_START_DATE, cache=cache
        )
