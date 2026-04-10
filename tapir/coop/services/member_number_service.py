from __future__ import annotations

from django.db.models import Max

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import legal_status_is_cooperative


class MemberNumberService:
    @classmethod
    def format_member_no(
        cls, member_no: int | None, cache: dict | None = None
    ) -> str | None:
        if member_no is None:
            return None

        prefix = get_parameter_value(ParameterKeys.MEMBER_NUMBER_PREFIX, cache=cache)
        length = get_parameter_value(
            ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, cache=cache
        )

        number_str = f"{member_no:0{length}}"
        return f"{prefix}{number_str}"

    @classmethod
    def compute_next_member_no(cls, cache: dict | None = None) -> int:
        start_value = get_parameter_value(
            ParameterKeys.MEMBER_NUMBER_START_VALUE, cache=cache
        )
        max_existing = Member.objects.aggregate(Max("member_no"))["member_no__max"] or 0
        return max(start_value, max_existing + 1)

    @classmethod
    def is_member_in_subscription_or_coop_trial(
        cls, member, cache: dict | None = None
    ) -> bool:
        if cache is None:
            cache = {}

        if MembershipCancellationManager.is_in_coop_trial(member):
            return True

        trial_subs = TrialPeriodManager.get_subscriptions_in_trial_period(
            member_id=member.id, cache=cache
        )
        return len(trial_subs) > 0

    @classmethod
    def should_assign_member_no(cls, member, cache: dict | None = None) -> bool:
        if member.member_no is not None:
            return False

        if cache is None:
            cache = {}

        only_after_trial = get_parameter_value(
            ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, cache=cache
        )
        if not only_after_trial:
            return True

        if legal_status_is_cooperative(cache=cache):
            return not MembershipCancellationManager.is_in_coop_trial(member)

        return not cls.is_member_in_subscription_or_coop_trial(member, cache=cache)

    @classmethod
    def assign_member_no_if_eligible(cls, member, cache: dict | None = None) -> bool:
        if not cls.should_assign_member_no(member, cache=cache):
            return False

        member.member_no = cls.compute_next_member_no(cache=cache)
        member.save()
        return True
