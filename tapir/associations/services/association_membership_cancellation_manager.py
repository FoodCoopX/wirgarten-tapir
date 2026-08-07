import datetime

from django.core.exceptions import ValidationError
from django.db import transaction

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationMembership,
    AssociationMembershipUpdatedLogEntry,
    AssociationMembershipDeletedLogEntry,
)
from tapir.log.util import freeze_for_log
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member
from tapir.wirgarten.service.products import get_active_and_future_subscriptions
from tapir.wirgarten.utils import get_now, get_today


class AssociationMembershipCancellationManager:
    @classmethod
    def does_member_have_a_cancellable_membership(
        cls, member: Member, reference_date: datetime.date, cache: dict
    ):
        return any(
            cls._can_membership_be_cancelled(
                membership=membership, reference_date=reference_date
            )
            for membership in TapirCache.get_member_association_memberships(
                member=member, cache=cache
            )
        )

    @classmethod
    def _can_membership_be_cancelled(
        cls, membership: AssociationMembership, reference_date: datetime.date
    ):
        if membership.cancellation_ts is not None:
            return False
        if membership.end_date is not None and membership.end_date <= reference_date:
            return False
        return True

    @classmethod
    @transaction.atomic
    def cancel_association_membership(
        cls,
        member: Member,
        end_date: datetime.date,
        actor: TapirUser,
        cache: dict,
    ):
        current_membership = TapirCache.get_member_association_membership_at_date(
            cache=cache, member=member, reference_date=end_date
        )
        if current_membership is not None:
            cls._set_membership_end_date(
                membership=current_membership,
                end_date=end_date,
                actor=actor,
                cache=cache,
            )

        for membership in TapirCache.get_member_association_memberships(
            member=member, cache=cache
        ):
            if membership.start_date > end_date:
                AssociationMembershipDeletedLogEntry().populate_membership(
                    membership=membership, actor=actor
                ).save()
                membership.delete()

    @classmethod
    def _set_membership_end_date(
        cls,
        membership: AssociationMembership,
        end_date: datetime.date,
        actor: TapirUser,
        cache: dict,
    ):
        before_changes = freeze_for_log(membership)
        membership.end_date = end_date
        membership.cancellation_ts = get_now(cache=cache)
        membership.save()
        AssociationMembershipUpdatedLogEntry().populate(
            old_frozen=before_changes,
            new_model=membership,
            actor=actor,
            user=membership.member,
        ).save()

    @classmethod
    def get_earliest_possible_membership_cancellation_date(
        cls, member: Member, cache: dict
    ):
        if (
            get_active_and_future_subscriptions(cache=cache)
            .filter(member=member, cancellation_ts__isnull=True)
            .exists()
        ):
            raise ValidationError("Dieses Mitglied hat aktive Verträge")

        latest_subscription = (
            get_active_and_future_subscriptions(cache=cache)
            .filter(member=member, cancellation_ts__isnull=False)
            .order_by("end_date")
            .last()
        )
        if latest_subscription is None:
            return get_today(cache=cache)
        return latest_subscription.end_date
