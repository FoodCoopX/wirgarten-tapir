from tapir.subscriptions.services.admin_subscription_addition_validator import (
    AdminSubscriptionAdditionValidator,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.start_date_week_options_builder import (
    StartDateWeekOptionsBuilder,
)
from tapir.subscriptions.types import DateOption, StartDateOptions
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import ProductType
from tapir.wirgarten.utils import get_today


class AdminSubscriptionAdditionDateOptionsBuilder:
    @classmethod
    def build(cls, product_type: ProductType, cache: dict) -> StartDateOptions:
        today = get_today(cache=cache)
        next_possible_start = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=today, apply_buffer_time=True, cache=cache
        )
        last_date = AdminSubscriptionAdditionValidator.get_last_possible_start_date(
            cache=cache
        )
        next_growing_period = TapirCache.get_first_growing_period_starting_after(
            reference_date=today, cache=cache
        )

        return StartDateOptions(
            next_possible_start=DateOption(
                date=next_possible_start,
                enabled=last_date is not None and next_possible_start <= last_date,
            ),
            weeks=(
                StartDateWeekOptionsBuilder.build_week_options(
                    product_type=product_type,
                    first_date=today,
                    last_date=last_date,
                    next_possible_start=next_possible_start,
                    cache=cache,
                )
                if last_date is not None
                else []
            ),
            next_period_start=DateOption(
                date=(
                    next_growing_period.start_date
                    if next_growing_period is not None
                    else None
                ),
                enabled=next_growing_period is not None,
            ),
        )
