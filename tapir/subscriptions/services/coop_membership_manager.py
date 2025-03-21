import datetime

from tapir.wirgarten.models import Member, CoopShareTransaction
from tapir.wirgarten.utils import get_today


class CoopMembershipManager:
    @staticmethod
    def can_member_cancel_coop_membership(
        member: Member, reference_date: datetime.date | None = None
    ):
        if reference_date is None:
            reference_date = get_today()

        return (
            member.coop_entry_date is not None
            and member.coop_entry_date > reference_date
        )

    @staticmethod
    def cancel_coop_membership(
        member: Member, reference_date: datetime.date | None = None
    ):
        if reference_date is None:
            reference_date = get_today()

        member.coopsharetransaction_set.filter(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at__gte=reference_date,
        ).delete()
