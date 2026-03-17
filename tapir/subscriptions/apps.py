from django.apps import AppConfig
from tapir_mail.registries import mail_segment_providers

from tapir.wirgarten.parameter_keys import ParameterKeys


class SubscriptionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.subscriptions"

    def ready(self):
        mail_segment_providers.add(self.provide_subscription_mail_segments)

    @classmethod
    def provide_subscription_mail_segments(cls):
        from tapir.wirgarten.models import Member
        from tapir.generic_exports.services.member_segment_provider import (
            MemberSegmentProvider,
        )
        from tapir.configuration.parameter import get_parameter_value
        from tapir.wirgarten.tapirmail import Segments

        segment_registry = {
            Segments.WITH_ACTIVE_SUBSCRIPTION: Member.objects.with_active_subscription,
            Segments.WITHOUT_ACTIVE_SUBSCRIPTION: Member.objects.without_active_subscription,
            Segments.MEMBERS_WITH_CONTRACT_SINCE_MORE_THAN_ONE_YEAR_BUT_NO: MemberSegmentProvider.get_queryset_members_with_contract_since_more_than_one_year_but_no_coop_share,
        }

        cache = {}

        trial_period_enabled = get_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
        )
        if trial_period_enabled:
            segment_registry["Mitglieder im Probezeit"] = (
                lambda: cls.get_queryset_members_in_trial(cache)
            )

        return segment_registry

    @staticmethod
    def get_queryset_members_in_trial(cache: dict):
        from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
        from tapir.wirgarten.models import Member
        from tapir.wirgarten.service.products import get_active_and_future_subscriptions
        from tapir.wirgarten.utils import get_today

        today = get_today(cache)
        subscriptions_in_trial = [
            subscription
            for subscription in get_active_and_future_subscriptions(
                reference_date=today, cache=cache
            )
            if TrialPeriodManager.is_contract_in_trial(
                subscription, reference_date=today, cache=cache
            )
        ]
        member_ids_in_trial = {
            subscription.member_id for subscription in subscriptions_in_trial
        }
        return Member.objects.filter(id__in=member_ids_in_trial)
