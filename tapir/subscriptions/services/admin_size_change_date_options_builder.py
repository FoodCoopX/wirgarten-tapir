import datetime
from dataclasses import dataclass

from tapir.deliveries.services.delivery_date_calculator import (
    DeliveryDateCalculator,
)
from tapir.subscriptions.services.admin_size_change_validator import (
    AdminSizeChangeValidator,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.utils import get_today


@dataclass(frozen=True)
class DateOption:
    date: datetime.date | None
    enabled: bool


@dataclass(frozen=True)
class WeekOption:
    date: datetime.date
    is_before_next_possible_start: bool
    has_no_delivery: bool


@dataclass(frozen=True)
class SizeChangeDateOptions:
    next_possible_start: DateOption
    weeks: list[WeekOption]
    next_period_start: DateOption


class AdminSizeChangeDateOptionsBuilder:
    @classmethod
    def build(cls, subscription: Subscription, cache: dict) -> SizeChangeDateOptions:
        # The possible options are for when the change applies:
        # - According to normal contract start rules
        # - On a user-chosen week
        # - At the start of the next growing period.

        next_possible_start = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=get_today(cache=cache), apply_buffer_time=True, cache=cache
        )
        return SizeChangeDateOptions(
            next_possible_start=DateOption(
                date=next_possible_start,
                enabled=subscription.start_date
                <= next_possible_start
                <= subscription.end_date,
            ),
            weeks=cls.build_week_options(
                subscription=subscription,
                next_possible_start=next_possible_start,
                cache=cache,
            ),
            next_period_start=cls.build_next_period_option(
                subscription=subscription, cache=cache
            ),
        )

    @classmethod
    def build_week_options(
        cls,
        subscription: Subscription,
        next_possible_start: datetime.date,
        cache: dict,
    ) -> list[WeekOption]:
        first_date = max(get_today(cache=cache), subscription.start_date)
        monday = get_monday(first_date)
        if monday < first_date:
            monday += datetime.timedelta(weeks=1)

        product_type = subscription.product.type
        week_options = []
        while monday <= subscription.end_date:
            week_options.append(
                WeekOption(
                    date=monday,
                    is_before_next_possible_start=monday < next_possible_start,
                    has_no_delivery=product_type.delivery_cycle != NO_DELIVERY[0]
                    and not DeliveryDateCalculator.is_week_delivered(
                        product_type=product_type,
                        delivery_date=monday,
                        check_for_weeks_without_delivery=True,
                        cache=cache,
                    ),
                )
            )
            monday += datetime.timedelta(weeks=1)
        return week_options

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
