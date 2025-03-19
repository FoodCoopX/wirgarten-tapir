from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_next_growing_period,
)
from tapir.wirgarten.utils import get_today


class AutomaticSubscriptionRenewalService:
    @classmethod
    def renew_subscriptions_if_necessary(cls):
        if not get_parameter_value(Parameter.SUBSCRIPTION_AUTOMATIC_RENEWAL):
            return

        for subscription in get_active_subscriptions():
            if cls.must_subscription_be_renewed(subscription):
                cls.renew_subscription(subscription)

    @classmethod
    def must_subscription_be_renewed(cls, subscription: Subscription) -> bool:
        if not get_parameter_value(Parameter.SUBSCRIPTION_AUTOMATIC_RENEWAL):
            return False

        if subscription.cancellation_ts is not None:
            return False

        next_growing_period = get_next_growing_period()
        if not next_growing_period:
            return False

        if Subscription.objects.filter(
            member=subscription.member,
            period=next_growing_period,
            product=subscription.product,
        ).exists():
            return False

        max_cancellation_date = NoticePeriodManager.get_max_cancellation_date(
            subscription
        )
        if max_cancellation_date >= get_today():
            return False

        return True

    @classmethod
    def renew_subscription(cls, subscription: Subscription):
        next_growing_period = get_next_growing_period()

        trial_disabled, trial_end_date_override = (
            cls.get_renewed_subscription_trial_data(subscription)
        )
        Subscription.objects.create(
            member=subscription.member,
            period=next_growing_period,
            product=subscription.product,
            quantity=subscription.quantity,
            start_date=next_growing_period.start_date,
            end_date=next_growing_period.end_date,
            solidarity_price=subscription.solidarity_price,
            solidarity_price_absolute=subscription.solidarity_price_absolute,
            mandate_ref=subscription.mandate_ref,
            trial_disabled=trial_disabled,
            trial_end_date_override=trial_end_date_override,
            notice_period_duration_in_months=NoticePeriodManager.get_notice_period_duration(
                subscription.product.type, next_growing_period
            ),
        )

    @classmethod
    def get_renewed_subscription_trial_data(cls, old_subscription: Subscription):
        # returns (trial_disabled, trial_end_date_override)

        trial_end_date = TrialPeriodManager.get_end_of_trial_period(old_subscription)
        if trial_end_date > old_subscription.end_date:
            return False, trial_end_date

        return True, None
