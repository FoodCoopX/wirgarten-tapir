import datetime

from dateutil.relativedelta import relativedelta

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class PaymentDueDateCalculator:
    @staticmethod
    def get_first_due_date_on_or_after(
        earliest_date: datetime.date, cache: dict
    ) -> datetime.date:
        due_date = earliest_date.replace(day=1) + relativedelta(
            day=get_parameter_value(ParameterKeys.PAYMENT_DUE_DAY, cache=cache)
        )
        if due_date < earliest_date:
            due_date += relativedelta(months=1)
        return due_date
