from __future__ import annotations

import datetime

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import IntegrityError, connection, transaction
from django.db.models import Max
from django.utils.translation import gettext_lazy as _

from tapir.accounts.models import UpdateTapirUserLogEntry, TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.coop.models import RetiredMemberNumber
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
    DUPLICATE_NUMBER_MESSAGE = _("Diese Mitgliedsnummer ist bereits vergeben.")
    RETIRED_NUMBER_MESSAGE = _("Diese Mitgliedsnummer ist bereits reserviert.")

    @classmethod
    def raise_if_number_conflict(cls, error: IntegrityError):
        constraint_name = getattr(
            getattr(error.__cause__, "diag", None), "constraint_name", None
        )
        if not constraint_name:
            return
        with connection.cursor() as cursor:
            constraint = connection.introspection.get_constraints(
                cursor, Member._meta.db_table
            ).get(constraint_name, {})
        if constraint.get("unique") and constraint.get("columns") == ["member_no"]:
            raise ValidationError(
                {"member_no": cls.DUPLICATE_NUMBER_MESSAGE}
            ) from error

    @classmethod
    def validate_member_number_available(
        cls, member_number: int | None, member_id: str | None
    ):
        if member_number is None:
            return
        if (
            Member.objects.filter(member_no=member_number)
            .exclude(pk=member_id)
            .exists()
        ):
            raise ValidationError({"member_no": cls.DUPLICATE_NUMBER_MESSAGE})
        reserved = RetiredMemberNumber.objects.filter(number=member_number)
        if member_id is not None:
            reserved = reserved.exclude(member_id=member_id)
        if reserved.exists():
            raise ValidationError({"member_no": cls.RETIRED_NUMBER_MESSAGE})

    @classmethod
    def set_member_number(
        cls, member: Member, member_number: int, actor: TapirUser
    ) -> bool:
        MinValueValidator(1)(member_number)
        try:
            with transaction.atomic():
                current = Member.objects.select_for_update().get(pk=member.pk)
                if current.member_no == member_number:
                    return False
                cls.validate_member_number_available(member_number, current.pk)
                before = freeze_for_log(current)
                if current.member_no is not None:
                    RetiredMemberNumber.objects.get_or_create(
                        number=current.member_no, defaults={"member": current}
                    )
                current.member_no = member_number
                current.save(update_fields=["member_no"])
                UpdateTapirUserLogEntry().populate(
                    old_frozen=before, new_model=current, user=current, actor=actor
                ).save()
        except IntegrityError as error:
            cls.raise_if_number_conflict(error)
            raise
        member.member_no = member_number
        return True

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
        max_retired = (
            RetiredMemberNumber.objects.aggregate(Max("number"))["number__max"] or 0
        )
        return max(start_value, max(max_existing, max_retired) + 1)

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
