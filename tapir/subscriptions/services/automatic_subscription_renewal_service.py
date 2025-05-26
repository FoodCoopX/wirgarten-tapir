import datetime
from typing import Dict, Callable

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_next_growing_period,
    get_current_growing_period,
)
from tapir.wirgarten.utils import get_today


class AutomaticSubscriptionRenewalService:
    @classmethod
    def renew_subscriptions_if_necessary(cls):
        cache = {}
        if not get_parameter_value(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=cache
        ):
            return

        for subscription in get_active_subscriptions():
            if cls.must_subscription_be_renewed(subscription, cache=cache):
                cls.renew_subscription(subscription, cache=cache)

    @classmethod
    def must_subscription_be_renewed(
        cls, subscription: Subscription, cache: Dict
    ) -> bool:
        if not get_parameter_value(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=cache
        ):
            return False

        if subscription.cancellation_ts is not None:
            return False

        next_growing_period = get_next_growing_period(cache=cache)
        if not next_growing_period:
            return False

        if Subscription.objects.filter(
            member=subscription.member,
            period=next_growing_period,
            product=subscription.product,
        ).exists():
            return False

        max_cancellation_date = NoticePeriodManager.get_max_cancellation_date(
            subscription, cache=cache
        )
        if max_cancellation_date >= get_today():
            return False

        return True

    @classmethod
    def renew_subscription(cls, subscription: Subscription, cache: Dict):
        next_growing_period = get_next_growing_period(cache=cache)

        trial_disabled, trial_end_date_override = (
            cls.get_renewed_subscription_trial_data(subscription, cache=cache)
        )
        Subscription.objects.create(
            member=subscription.member,
            period=next_growing_period,
            product=subscription.product,
            quantity=subscription.quantity,
            start_date=next_growing_period.start_date,
            end_date=next_growing_period.end_date,
            solidarity_price_percentage=subscription.solidarity_price_percentage,
            solidarity_price_absolute=subscription.solidarity_price_absolute,
            mandate_ref=subscription.mandate_ref,
            trial_disabled=trial_disabled,
            trial_end_date_override=trial_end_date_override,
            notice_period_duration=NoticePeriodManager.get_notice_period_duration(
                subscription.product.type, next_growing_period, cache=cache
            ),
        )

    @classmethod
    def get_renewed_subscription_trial_data(
        cls, old_subscription: Subscription, cache: Dict
    ):
        # returns (trial_disabled, trial_end_date_override)

        if not get_parameter_value(ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache):
            return True, None

        trial_end_date = TrialPeriodManager.get_end_of_trial_period(
            old_subscription, cache=cache
        )
        if trial_end_date is not None and trial_end_date > old_subscription.end_date:
            return False, trial_end_date

        return True, None

    @classmethod
    def get_subscriptions_that_will_be_renewed(
        cls, reference_date: datetime.date, cache: Dict
    ):
        if not get_parameter_value(ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache):
            return set()

        current_growing_period = get_current_growing_period(reference_date, cache)
        if current_growing_period is None:
            return set()

        current_subscriptions = TapirCache.get_subscriptions_active_at_date(
            reference_date, cache
        )

        members_ids_currently_subbed_to_product_id = {
            product.id: set() for product in TapirCache.get_all_products(cache)
        }
        for subscription in current_subscriptions:
            members_ids_currently_subbed_to_product_id[subscription.product_id].add(
                subscription.member_id
            )

        end_of_previous_growing_period = (
            current_growing_period.start_date - datetime.timedelta(days=1)
        )
        subscriptions_from_previous_growing_period = (
            TapirCache.get_subscriptions_active_at_date(
                end_of_previous_growing_period, cache
            )
        )

        return {
            subscription
            for subscription in subscriptions_from_previous_growing_period
            if subscription.cancellation_ts is None
            and subscription.member_id
            not in members_ids_currently_subbed_to_product_id[subscription.product_id]
        }

    @classmethod
    def get_subscriptions_and_renewals(
        cls,
        reference_date: datetime.date,
        subscription_filter: Callable[[Subscription], bool],
        cache: Dict,
    ):
        subscriptions = TapirCache.get_subscriptions_active_at_date(
            reference_date=reference_date, cache=cache
        )
        relevant_subscriptions = set(filter(subscription_filter, subscriptions))

        all_renewed_subscriptions = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=reference_date, cache=cache
            )
        )
        relevant_renewed_subscriptions = set(
            filter(subscription_filter, all_renewed_subscriptions)
        )

        relevant_subscriptions.update(relevant_renewed_subscriptions)

        return relevant_subscriptions
