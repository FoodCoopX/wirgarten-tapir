from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.models import Product, Member
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import get_active_and_future_subscriptions
from tapir.wirgarten.utils import get_now


class SubscriptionCancellationManager:
    @classmethod
    def get_earliest_possible_cancellation_date(cls, product: Product, member: Member):
        if not get_parameter_value(Parameter.SUBSCRIPTION_AUTOMATIC_RENEWAL):
            raise ImproperlyConfigured(
                "Subscriptions don't have a cancellation date if automatic subscription renewal is disabled"
            )

        subscriptions = (
            get_active_and_future_subscriptions()
            .filter(member=member, product=product)
            .order_by("start_date")
        )
        for subscription in subscriptions:
            if TrialPeriodManager.is_subscription_in_trial(subscription):
                return TrialPeriodManager.get_earliest_trial_cancellation_date()

        return subscriptions.last().end_date

    @classmethod
    def cancel_subscriptions(cls, product: Product, member: Member):
        cancellation_date = cls.get_earliest_possible_cancellation_date(
            product=product, member=member
        )

        for subscription in get_active_and_future_subscriptions().filter(
            member=member, product=product
        ):
            if subscription.start_date > cancellation_date:
                subscription.delete()
                continue

            subscription.cancellation_ts = get_now()
            subscription.end_date = cancellation_date
            subscription.save()
