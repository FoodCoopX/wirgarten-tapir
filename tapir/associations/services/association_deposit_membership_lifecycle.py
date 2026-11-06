import json

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositMembershipChangedLogEntry,
    AssociationMembership,
)
from tapir.associations.services.association_deposit_membership_coverage import (
    AssociationDepositMembershipCoverage,
)
from tapir.log.util import freeze_for_log
from tapir.wirgarten.utils import get_today


class AssociationDepositMembershipLifecycle:
    @staticmethod
    def get_membership_snapshot(member, cache: dict) -> list[dict]:
        return list(
            AssociationMembership.objects.filter(member=member)
            .order_by("pk")
            .values("pk", "type_id", "start_date", "end_date", "cancellation_ts")
        )

    @classmethod
    def record_membership_change(cls, member, previous, actor, cache: dict):
        AssociationDepositMembershipCoverage.invalidate_member(member, cache)
        account = AssociationDepositAccount.objects.filter(member=member).first()
        current = cls.get_membership_snapshot(member, cache)
        if account is None or previous == current:
            return
        old = freeze_for_log(account)
        cutoff = account.collection_stopped_from
        if (
            cutoff
            and any(row["start_date"] < cutoff for row in previous)
            and (
                cutoff > get_today(cache)
                or any(row["start_date"] == cutoff for row in current)
            )
        ):
            account.collection_stopped_from = None
        account.collection_stopped_from = (
            AssociationDepositMembershipCoverage.get_collection_cutoff(account, cache)
        )
        if not current and account.collection_stopped_from is None:
            account.collection_stopped_from = get_today(cache)
        account.agreement_revision += 1
        account.save(
            update_fields=[
                "collection_stopped_from",
                "agreement_revision",
                "updated_at",
            ]
        )
        values = freeze_for_log(account)
        values.update(
            previous_account=json.dumps(old, sort_keys=True),
            previous_memberships=json.dumps(previous, default=str, sort_keys=True),
            memberships=json.dumps(current, default=str, sort_keys=True),
            payments=json.dumps(
                [
                    freeze_for_log(payment)
                    for payment in account.payments.order_by("pk")
                ],
                sort_keys=True,
            ),
        )
        AssociationDepositMembershipChangedLogEntry().populate(
            frozen=values, actor=actor, user=member
        ).save()
