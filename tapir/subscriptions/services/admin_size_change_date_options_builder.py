import datetime
from tapir.subscriptions.services.admin_size_change_validator import (
    AdminSizeChangeValidator,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.start_date_week_options_builder import (
    StartDateWeekOptionsBuilder,
)
from tapir.subscriptions.types import DateOption, StartDateOptions
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.utils import get_today


class AdminSizeChangeDateOptionsBuilder:
    @classmethod
    def build(cls, subscription: Subscription, cache: dict) -> StartDateOptions:
        # The possible options are for when the change applies:
        # - According to normal contract start rules
        # - On a user-chosen week
        # - At the start of the next growing period.

        next_possible_start = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=get_today(cache=cache), apply_buffer_time=True, cache=cache
        )
        return StartDateOptions(
            next_possible_start=DateOption(
                date=next_possible_start,
                enabled=subscription.start_date
                <= next_possible_start
                <= subscription.end_date,
            ),
            weeks=StartDateWeekOptionsBuilder.build_week_options(
                product_type=subscription.product.type,
                first_date=max(get_today(cache=cache), subscription.start_date),
                last_date=subscription.end_date,
                next_possible_start=next_possible_start,
                cache=cache,
            ),
            next_period_start=cls.build_next_period_option(
                subscription=subscription, cache=cache
            ),
        )

    @classmethod
    def build_next_period_option(
        cls, subscription: Subscription, cache: dict
    ) -> DateOption:
        next_growing_period = TapirCache.get_first_growing_period_starting_after(
            reference_date=get_today(cache=cache), cache=cache
        )
        if next_growing_period is None:
            return DateOption(date=None, enabled=False)

        change_date = next_growing_period.start_date
        return DateOption(
            date=change_date,
            enabled=subscription.start_date <= change_date <= subscription.end_date
            or AdminSizeChangeValidator.is_change_from_next_period(
                subscription=subscription, change_date=change_date, cache=cache
            ),
        )
