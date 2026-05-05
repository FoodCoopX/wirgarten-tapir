import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.utils.shortcuts import get_monday, get_next_sunday
from tapir.wirgarten.models import Subscription, Product, Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.get_next_delivery_date import get_next_delivery_date
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
    get_active_subscriptions,
)
from tapir.wirgarten.utils import get_today


class TrialPeriodManager:
    @classmethod
    def get_last_day_of_trial_period(
        cls, contract: Subscription | SolidarityContribution, cache: dict
    ):
        if contract.trial_disabled or not get_parameter_value(
            ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
        ):
            return None

        if contract.trial_end_date_override is not None:
            return contract.trial_end_date_override

        return cls.get_last_day_of_trial_period_by_weeks(contract, cache=cache)

    @classmethod
    def get_last_day_of_trial_period_by_weeks(
        cls, contract: Subscription | SolidarityContribution, cache: dict
    ) -> datetime.date:
        start_date = cls.get_trial_period_start_date(contract=contract, cache=cache)

        return (
            start_date
            + datetime.timedelta(
                weeks=get_parameter_value(
                    ParameterKeys.TRIAL_PERIOD_DURATION, cache=cache
                )
            )
            - datetime.timedelta(days=1)
        )

    @classmethod
    def get_trial_period_start_date(
        cls, contract: Subscription | SolidarityContribution, cache: dict
    ):
        # For subscriptions that are delivered, the trial period starts on the monday before the first delivery,
        # not on the contract start date

        product = getattr(contract, "product", None)
        if product is None:
            return contract.start_date

        pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                member_id=contract.member_id,
                reference_date=contract.start_date,
                cache=cache,
            )
        )
        date_of_first_delivery = (
            DeliveryDateCalculator.get_next_delivery_date_for_product_type(
                reference_date=contract.start_date,
                product_type=product.type,
                check_for_weeks_without_delivery=False,
                pickup_location_id=pickup_location_id,
                cache=cache,
            )
        )
        if date_of_first_delivery is None:
            date_of_first_delivery = contract.start_date
        return get_monday(date_of_first_delivery)

    @classmethod
    def is_contract_in_trial(
        cls,
        contract: Subscription | SolidarityContribution,
        cache: dict,
        reference_date: datetime.date = None,
    ) -> bool:
        if not get_parameter_value(ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache):
            return False

        if reference_date is None:
            reference_date = get_today(cache=cache)

        end_of_trial_period = cls.get_last_day_of_trial_period(contract, cache=cache)
        if end_of_trial_period is None:
            return False

        return end_of_trial_period >= reference_date

    @classmethod
    def get_earliest_trial_cancellation_date(
        cls,
        contract: Subscription | SolidarityContribution,
        cache: dict,
        reference_date: datetime.date = None,
    ) -> datetime.date:
        if not get_parameter_value(
            ParameterKeys.TRIAL_PERIOD_CAN_BE_CANCELLED_BEFORE_END, cache=cache
        ):
            return cls.get_last_day_of_trial_period(contract, cache=cache)

        if reference_date is None:
            reference_date = get_today(cache=cache)

        next_delivery_date = get_next_delivery_date(reference_date, cache=cache)
        date_limit = DateLimitForDeliveryChangeCalculator.calculate_date_limit_for_delivery_changes_in_week(
            next_delivery_date, cache=cache
        )
        if date_limit >= reference_date:
            return get_next_sunday(reference_date)

        return get_next_sunday(next_delivery_date)

    @classmethod
    def is_product_in_trial(
        cls,
        product: Product,
        member: Member,
        cache: dict,
        reference_date: datetime.date | None = None,
    ) -> bool:
        if not get_parameter_value(ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache):
            return False

        if reference_date is None:
            reference_date = get_today(cache=cache)

        return cls.is_contract_in_trial(
            contract=get_active_and_future_subscriptions(
                reference_date=reference_date, cache=cache
            )
            .filter(member=member, product=product)
            .order_by("start_date")
            .first(),
            reference_date=reference_date,
            cache=cache,
        )

    @classmethod
    def get_subscriptions_in_trial_period(
        cls, member_id: str, reference_date: datetime.date = None, cache: dict = None
    ) -> list[Subscription]:
        if not get_parameter_value(ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache):
            return []

        subscriptions = get_active_and_future_subscriptions(cache=cache).filter(
            member_id=member_id,
        )

        return list(
            filter(
                lambda subscription: cls.is_contract_in_trial(
                    subscription, reference_date=reference_date, cache=cache
                ),
                subscriptions,
            )
        )

    @classmethod
    def get_earliest_trial_period_end_date_for_product_type(
        cls,
        member_id: str,
        product_type_id: str,
        reference_date: datetime.date,
        cache: dict,
    ):
        subscriptions = get_active_subscriptions(
            reference_date=reference_date, cache=cache
        ).filter(member_id=member_id, product__type_id=product_type_id)
        trial_end_dates = [
            cls.get_last_day_of_trial_period(subscription, cache)
            for subscription in subscriptions
        ]
        if None in trial_end_dates:
            return None

        return min(trial_end_dates)
