import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.models import GrowingPeriod
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class ContractStartDateCalculator:
    @classmethod
    def get_next_contract_start_date(
        cls, reference_date: datetime.date, apply_buffer_time: bool, cache: dict
    ):
        current_date = get_monday(reference_date)
        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=reference_date, cache=cache
        )
        if growing_period is not None and current_date < growing_period.start_date:
            current_date += datetime.timedelta(weeks=1)

        while not cls.can_contract_start_in_week(
            reference_date=current_date,
            apply_buffer_time=apply_buffer_time,
            cache=cache,
        ):
            current_date += datetime.timedelta(weeks=1)

        return current_date

    @classmethod
    def can_contract_start_in_week(
        cls, reference_date: datetime.date, apply_buffer_time: bool, cache: dict
    ) -> bool:
        date_limit = DateLimitForDeliveryChangeCalculator.calculate_date_limit_for_delivery_changes_in_week(
            reference_date=reference_date, cache=cache
        )

        if apply_buffer_time:
            date_limit -= datetime.timedelta(
                days=get_parameter_value(
                    key=ParameterKeys.SUBSCRIPTION_BUFFER_TIME_BEFORE_START, cache=cache
                )
            )

        return date_limit >= get_today(cache=cache)

    @classmethod
    def get_next_contract_start_date_in_growing_period(
        cls, growing_period: GrowingPeriod, apply_buffer_time: bool, cache: dict
    ):
        today = get_today(cache=cache)
        if growing_period.start_date <= today:
            reference_date = today
        else:
            reference_date = growing_period.start_date

        contract_start_date = cls.get_next_contract_start_date(
            reference_date=reference_date,
            apply_buffer_time=apply_buffer_time,
            cache=cache,
        )

        return contract_start_date
