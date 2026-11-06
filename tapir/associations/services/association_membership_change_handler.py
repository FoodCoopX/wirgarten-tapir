import datetime

from django.db import transaction
from django.db.models import Q

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationMembershipType,
    AssociationMembership,
    AssociationMembershipDeletedLogEntry,
    AssociationMembershipUpdatedLogEntry,
    AssociationMembershipCreatedLogEntry,
)
from tapir.associations.services.association_deposit_membership_lifecycle import (
    AssociationDepositMembershipLifecycle,
)
from tapir.log.util import freeze_for_log
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_now


class AssociationMembershipChangeHandler:
    @classmethod
    @transaction.atomic
    def start_membership(
        cls,
        member: Member,
        association_membership_type: AssociationMembershipType,
        start_date: datetime.date,
        actor: TapirUser,
        cache: dict,
    ):
        Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        previous = AssociationDepositMembershipLifecycle.get_membership_snapshot(
            member, cache
        )
        member_memberships = AssociationMembership.objects.filter(member=member)

        memberships_to_delete = member_memberships.filter(start_date__gte=start_date)
        for membership in memberships_to_delete:
            AssociationMembershipDeletedLogEntry().populate_membership(
                membership=membership, actor=actor
            ).save()
        memberships_to_delete.delete()

        memberships_to_update = member_memberships.filter(
            Q(end_date=None) | Q(end_date__gte=start_date)
        )
        for membership in memberships_to_update:
            before_changes = freeze_for_log(membership)
            membership.end_date = start_date - datetime.timedelta(days=1)
            membership.cancellation_ts = get_now(cache=cache)
            membership.save()
            AssociationMembershipUpdatedLogEntry().populate(
                old_frozen=before_changes,
                new_model=membership,
                user=membership.member,
                actor=actor,
            ).save()

        membership = AssociationMembership.objects.create(
            type=association_membership_type, member=member, start_date=start_date
        )
        AssociationMembershipCreatedLogEntry().populate_membership(
            membership=membership,
            actor=actor,
        ).save()
        AssociationDepositMembershipLifecycle.record_membership_change(
            member, previous, actor, cache
        )
        return membership

    @staticmethod
    @transaction.atomic
    def set_end_date(membership, end_date, actor, cache: dict):
        Member.objects.select_for_update(no_key=True).get(pk=membership.member_id)
        membership = AssociationMembership.objects.get(pk=membership.pk)
        previous = AssociationDepositMembershipLifecycle.get_membership_snapshot(
            membership.member, cache
        )
        old = freeze_for_log(membership)
        end_date_before = membership.end_date
        membership.end_date = end_date
        membership.cancellation_ts = get_now(cache=cache)
        membership.save()
        AssociationMembershipUpdatedLogEntry().populate(
            old_frozen=old, new_model=membership, actor=actor, user=membership.member
        ).save()
        AssociationDepositMembershipLifecycle.record_membership_change(
            membership.member, previous, actor, cache
        )
        return membership, end_date_before
