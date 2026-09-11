from __future__ import annotations

import datetime

from django.db import transaction
from django.db.models import Max

from tapir.accounts.models import UpdateTapirUserLogEntry, TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.coop_membership_cancellation_manager import (
    CoopMembershipCancellationManager,
)
from tapir.log.util import freeze_for_log
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, CoopShareTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import (
    legal_status_is_cooperative,
    legal_status_is_association,
)


class MemberNumberService:
    @staticmethod
    def build_formatted_number(member_number: int, prefix: str, length: int) -> str:
        return f"{prefix}{member_number:0{length}}"

    @classmethod
    def format_member_number(cls, member_number: int | None, cache: dict) -> str | None:
        if member_number is None:
            return None

        prefix = get_parameter_value(ParameterKeys.MEMBER_NUMBER_PREFIX, cache=cache)
        length = get_parameter_value(
            ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, cache=cache
        )

        return cls.build_formatted_number(member_number, prefix, length)

    @classmethod
    def compute_next_member_number(cls, cache: dict) -> int:
        start_value = get_parameter_value(
            ParameterKeys.MEMBER_NUMBER_START_VALUE, cache=cache
        )
        max_existing = Member.objects.aggregate(Max("member_no"))["member_no__max"] or 0
        return max(start_value, max_existing + 1)

    @classmethod
    def is_member_in_subscription_trial(cls, member: Member, cache: dict) -> bool:
        trial_subs = TrialPeriodManager.get_subscriptions_in_trial_period(
            member_id=member.id, cache=cache
        )
        return len(trial_subs) > 0

    @classmethod
    def should_assign_member_number(cls, member: Member) -> bool:
        return member.member_no is None

    @classmethod
    def should_display_member_number(
        cls, member: Member, reference_date: datetime.date, cache: dict
    ) -> bool:
        if member.member_no is None:
            return False

        only_after_trial = get_parameter_value(
            ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, cache=cache
        )
        if not only_after_trial:
            return True

        if legal_status_is_cooperative(cache=cache):
            if not CoopShareTransaction.objects.filter(member=member).exists():
                return False
            return not CoopMembershipCancellationManager.is_in_coop_trial(
                member=member, reference_date=reference_date, cache=cache
            )

        if legal_status_is_association(cache=cache):
            return any(
                membership.start_date < reference_date
                for membership in TapirCache.get_member_association_memberships(
                    member=member, cache=cache
                )
            )
        return not cls.is_member_in_subscription_trial(member, cache=cache)

    @classmethod
    def assign_member_number_if_eligible(
        cls, member: Member, cache: dict, actor: TapirUser | None
    ) -> bool:
        if not cls.should_assign_member_number(member):
            return False

        member_before = freeze_for_log(member)
        member.member_no = cls.compute_next_member_number(cache=cache)
        log_entry = UpdateTapirUserLogEntry().populate(
            old_frozen=member_before,
            new_model=member,
            user=member,
            actor=actor,
        )

        with transaction.atomic():
            member.save()
            log_entry.save()

        return True
