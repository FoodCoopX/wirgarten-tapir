import datetime

from django.db import transaction
from django.db.models import Q, QuerySet

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDeposit,
    AssociationMembershipType,
    AssociationMembership,
    AssociationMembershipDeletedLogEntry,
    AssociationMembershipUpdatedLogEntry,
    AssociationMembershipCreatedLogEntry,
)
from tapir.associations.services.association_deposit_membership_end_handler import (
    iter_continuous_memberships,
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
        member_memberships = AssociationMembership.objects.filter(member=member)
        previous_day = start_date - datetime.timedelta(days=1)
        deposits = cls._get_deposits_for_membership_change(
            member_memberships, previous_day
        )

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
            membership.end_date = previous_day
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
        for deposit in deposits:
            deposit.membership = membership
            deposit.save(update_fields=["membership", "updated_at"])
        AssociationMembershipCreatedLogEntry().populate_membership(
            membership=membership,
            actor=actor,
        ).save()
        return membership

    @staticmethod
    def _get_deposits_for_membership_change(
        memberships: QuerySet[AssociationMembership], previous_day: datetime.date
    ) -> list[AssociationDeposit]:
        for membership in iter_continuous_memberships(
            memberships.filter(Q(end_date=None) | Q(end_date__gte=previous_day))
            .prefetch_related("deposits")
            .order_by("start_date"),
            previous_day,
        ):
            deposits = list(membership.deposits.all())
            if deposits:
                return deposits
        return []
