from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.models import Product, Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import get_now, get_today


class SubscriptionCancellationManager:
    @classmethod
    def get_earliest_possible_cancellation_date_for_product(
        cls, product: Product, member: Member, cache: dict
    ):
        subscriptions_for_this_product = (
            get_active_and_future_subscriptions(cache=cache)
            .filter(member=member, product=product)
            .order_by("end_date")
        )
        subscriptions_for_this_product = [
            subscription
            for subscription in subscriptions_for_this_product
            if subscription.cancellation_ts is None
        ]
        earliest_subscription = subscriptions_for_this_product[0]
        if TrialPeriodManager.is_contract_in_trial(earliest_subscription):
            return TrialPeriodManager.get_earliest_trial_cancellation_date(
                earliest_subscription, cache=cache
            )

        return subscriptions_for_this_product[-1].end_date

    @classmethod
    def get_earliest_possible_cancellation_date_for_solidarity_contribution(
        cls, member: Member, cache: dict
    ):
        today = get_today(cache=cache)
        contributions = list(
            cls.get_solidarity_contributions_that_could_be_cancelled(
                member=member, cache=cache
            )
        )
        trial_end_dates = [
            TrialPeriodManager.get_earliest_trial_cancellation_date(
                contract=contribution, reference_date=today, cache=cache
            )
            for contribution in contributions
            if TrialPeriodManager.is_contract_in_trial(
                contract=contribution, reference_date=today, cache=cache
            )
        ]
        if len(trial_end_dates) == 0:
            return contributions[-1].end_date

        return min(trial_end_dates)

    @classmethod
    def get_solidarity_contributions_that_could_be_cancelled(
        cls, member: Member, cache: dict
    ):
        return SolidarityContribution.objects.filter(
            member=member, end_date__gte=get_today(cache=cache)
        ).order_by("end_date")

    @classmethod
    def cancel_subscriptions(cls, product: Product, member: Member, cache: dict):
        cancellation_date = cls.get_earliest_possible_cancellation_date_for_product(
            product=product, member=member, cache=cache
        )

        auto_renew_enabled = get_parameter_value(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=cache
        )

        cancelled_subscriptions = []
        deleted_subscriptions = []
        for subscription in get_active_and_future_subscriptions(cache=cache).filter(
            member=member, product=product, cancellation_ts__isnull=True
        ):
            if (
                not TrialPeriodManager.is_contract_in_trial(subscription, cache=cache)
                and not auto_renew_enabled
            ):
                raise ImproperlyConfigured(
                    "Subscriptions outside of trial period can only be cancelled if auto renew is enabled"
                )

            if subscription.start_date >= cancellation_date:
                subscription.delete()
                deleted_subscriptions.append(subscription)
                continue

            subscription.cancellation_ts = get_now(cache=cache)
            subscription.end_date = min(cancellation_date, subscription.end_date)
            subscription.save()
            cancelled_subscriptions.append(subscription)

        return cancelled_subscriptions, deleted_subscriptions
