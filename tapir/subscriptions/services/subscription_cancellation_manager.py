from typing import Dict

from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.models import Product, Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import get_now


class SubscriptionCancellationManager:
    @classmethod
    def get_earliest_possible_cancellation_date(
        cls, product: Product, member: Member, cache: Dict
    ):
        subscriptions_for_this_product = list(
            get_active_and_future_subscriptions(cache=cache)
            .filter(member=member, product=product)
            .order_by("end_date")
        )
        earliest_subscription = subscriptions_for_this_product[0]
        if TrialPeriodManager.is_subscription_in_trial(earliest_subscription):
            return TrialPeriodManager.get_earliest_trial_cancellation_date(cache=cache)

        return subscriptions_for_this_product[-1].end_date

    @classmethod
    def cancel_subscriptions(cls, product: Product, member: Member, cache: Dict):
        cancellation_date = cls.get_earliest_possible_cancellation_date(
            product=product, member=member, cache=cache
        )

        auto_renew_enabled = get_parameter_value(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=cache
        )

        cancelled_subscriptions = []
        for subscription in get_active_and_future_subscriptions(cache=cache).filter(
            member=member, product=product
        ):
            if (
                not TrialPeriodManager.is_subscription_in_trial(subscription)
                and not auto_renew_enabled
            ):
                raise ImproperlyConfigured(
                    "Subscriptions outside of trial period can only be cancelled if auto renew is enabled"
                )

            if subscription.start_date > cancellation_date:
                subscription.delete()
                continue

            subscription.cancellation_ts = get_now()
            subscription.end_date = cancellation_date
            subscription.save()
            cancelled_subscriptions.append(subscription)

        return cancelled_subscriptions
