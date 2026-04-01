import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import GrowingPeriod
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class GrowingPeriodChoiceProvider:
    @classmethod
    def get_available_growing_periods(cls, reference_date: datetime.date, cache: dict):
        all_growing_periods = TapirCache.get_all_growing_periods_ascending(cache=cache)
        start_date_threshold = get_today(cache=cache) + datetime.timedelta(
            days=get_parameter_value(
                key=ParameterKeys.ENABLE_GROWING_PERIOD_CHOICE_DAYS_BEFORE
            )
        )
        growing_periods = cls.filter_periods(
            growing_periods=all_growing_periods,
            reference_date=reference_date,
            threshold=start_date_threshold,
        )[:2]

        if len(growing_periods) == 2:
            contract_start_current_period = ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_periods[0], apply_buffer_time=True, cache=cache
            )
            contract_start_next_period = ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_periods[1], apply_buffer_time=True, cache=cache
            )
            if contract_start_next_period == contract_start_current_period:
                growing_periods = [growing_periods[1]]

        if len(growing_periods) == 0:
            growing_periods = cls.filter_periods(
                growing_periods=all_growing_periods,
                reference_date=reference_date,
                threshold=None,
            )[:1]

        return growing_periods

    @classmethod
    def filter_periods(
        cls,
        growing_periods: list[GrowingPeriod],
        reference_date: datetime.date,
        threshold: datetime.date | None,
    ):
        return [
            growing_period
            for growing_period in growing_periods
            if growing_period.end_date >= reference_date
            and growing_period.is_available_in_bestell_wizard
            and (threshold is None or growing_period.start_date <= threshold)
        ][:2]
