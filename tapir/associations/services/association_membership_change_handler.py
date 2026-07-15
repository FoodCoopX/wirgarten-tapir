import datetime

from django.db.models import Q

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationMembershipType,
    AssociationMembership,
    AssociationMembershipDeletedLogEntry,
    AssociationMembershipUpdatedLogEntry,
    AssociationMembershipCreatedLogEntry,
)
from tapir.log.util import freeze_for_log
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_now


class AssociationMembershipChangeHandler:
    @classmethod
    def start_membership(
        cls,
        member: Member,
        association_membership_type: AssociationMembershipType,
        start_date: datetime.date,
        actor: TapirUser,
        cache: dict,
    ):
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
        return membership
