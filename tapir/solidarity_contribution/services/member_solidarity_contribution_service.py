import datetime
from decimal import Decimal

from django.db.models import QuerySet, OuterRef, Subquery

from tapir.accounts.models import TapirUser
from tapir.solidarity_contribution.models import (
    SolidarityContribution,
    SolidarityContributionChangedLogEntry,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member
from tapir.wirgarten.service.products import get_next_growing_period
from tapir.wirgarten.utils import get_now


class MemberSolidarityContributionService:
    ANNOTATION_CURRENT_MEMBER_CONTRIBUTION = "current_member_contribution"
    ANNOTATION_FUTURE_MEMBER_CONTRIBUTION_AMOUNT = "future_member_contribution_amount"
    ANNOTATION_FUTURE_MEMBER_CONTRIBUTION_START_DATE = (
        "future_member_contribution_start_date"
    )

    @classmethod
    def get_member_contribution(
        cls, member_id: str, reference_date: datetime.date, cache: dict
    ):
        return TapirCache.get_member_solidarity_contribution_at_date(
            member_id=member_id, reference_date=reference_date, cache=cache
        )

    @classmethod
    def assign_contribution_to_member(
        cls,
        member: Member,
        change_date: datetime.date,
        amount: float | Decimal,
        cache: dict,
        actor: TapirUser,
    ):
        member_contributions = SolidarityContribution.objects.filter(
            member_id=member.id
        )
        last_contribution = (
            member_contributions.filter(
                end_date__gte=change_date - datetime.timedelta(days=1),
            )
            .order_by("start_date")
            .last()
        )
        member_contributions.filter(end_date__gte=change_date).update(
            end_date=change_date - datetime.timedelta(days=1),
            cancellation_ts=get_now(cache=cache),
        )
        if last_contribution:
            last_contribution.refresh_from_db()
        member_contributions.filter(start_date__gte=change_date).delete()

        if amount == 0:
            cls.create_log_entry_if_necessary(
                actor=actor,
                user=member,
                old_contribution=last_contribution,
                new_contribution=None,
            )
            return None

        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=change_date, cache=cache
        )
        if growing_period is None:
            future_growing_period = get_next_growing_period(
                reference_date=change_date, cache=cache
            )
            end_date = future_growing_period.start_date - datetime.timedelta(days=1)
        else:
            end_date = growing_period.end_date

        trial_disabled, trial_end_date_override = cls.get_trial_parameters(
            member_contributions.filter(start_date__lte=change_date)
            .order_by("start_date")
            .last(),
            cache,
        )

        new_contribution = SolidarityContribution.objects.create(
            member_id=member.id,
            amount=amount,
            start_date=change_date,
            end_date=end_date,
            trial_disabled=trial_disabled,
            trial_end_date_override=trial_end_date_override,
        )

        cls.create_log_entry_if_necessary(
            actor=actor,
            user=member,
            old_contribution=last_contribution,
            new_contribution=new_contribution,
        )

        return new_contribution

    @classmethod
    def get_trial_parameters(
        cls, contribution: SolidarityContribution | None, cache: dict
    ) -> tuple[bool, datetime.date | None]:
        if contribution is None:
            return False, None

        previous_trial_end_date = TrialPeriodManager.get_last_day_of_trial_period(
            contract=contribution, cache=cache
        )
        if previous_trial_end_date is None:
            return True, None

        return False, previous_trial_end_date

    @classmethod
    def create_log_entry_if_necessary(
        cls,
        actor: TapirUser,
        user: Member,
        old_contribution: SolidarityContribution | None,
        new_contribution: SolidarityContribution | None,
    ):
        if old_contribution is None and new_contribution is None:
            return

        SolidarityContributionChangedLogEntry().populate_solidarity_contribution(
            actor=actor,
            user=user,
            new_contribution=new_contribution,
            old_contribution=old_contribution,
        ).save()

    @classmethod
    def is_user_allowed_to_change_contribution(
        cls,
        logged_in_user: TapirUser,
        target_member_id: str,
        new_amount: Decimal,
        change_date: datetime.date,
        cache: dict,
    ):
        if logged_in_user.has_perm(Permission.Coop.MANAGE):
            return True

        current_contribution = (
            MemberSolidarityContributionService.get_member_contribution(
                member_id=target_member_id, reference_date=change_date, cache=cache
            )
        )

        return new_amount > current_contribution

    @classmethod
    def annotate_member_queryset_with_current_contribution(
        cls, queryset: QuerySet[Member], reference_date: datetime.date
    ):
        current_member_contribution = (
            SolidarityContribution.objects.filter(
                member=OuterRef("id"),
                start_date__lte=reference_date,
                end_date__gte=reference_date,
            )
            .order_by("-start_date")
            .values("amount")[:1]
        )

        return queryset.annotate(
            **{
                cls.ANNOTATION_CURRENT_MEMBER_CONTRIBUTION: Subquery(
                    current_member_contribution
                )
            }
        )

    @classmethod
    def annotate_member_queryset_with_future_contribution(
        cls, queryset: QuerySet[Member], reference_date: datetime.date
    ):
        future_member_contribution_amount = (
            SolidarityContribution.objects.filter(
                member=OuterRef("id"),
                start_date__gt=reference_date,
            )
            .order_by("start_date")
            .values("amount")[:1]
        )
        future_member_contribution_start_date = (
            SolidarityContribution.objects.filter(
                member=OuterRef("id"),
                start_date__gt=reference_date,
            )
            .order_by("start_date")
            .values("start_date")[:1]
        )

        return queryset.annotate(
            **{
                cls.ANNOTATION_FUTURE_MEMBER_CONTRIBUTION_AMOUNT: Subquery(
                    future_member_contribution_amount
                ),
                cls.ANNOTATION_FUTURE_MEMBER_CONTRIBUTION_START_DATE: Subquery(
                    future_member_contribution_start_date
                ),
            }
        )
