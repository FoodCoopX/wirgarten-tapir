import datetime

from tapir.wirgarten.models import Member, CoopShareTransaction
from tapir.wirgarten.utils import get_today


class MembershipCancellationManager:
    @classmethod
    def get_coop_entry_date(cls, member: Member):
        earliest_transaction = (
            member.coopsharetransaction_set.filter(
                transaction_type__in=[
                    CoopShareTransaction.CoopShareTransactionType.PURCHASE,
                    CoopShareTransaction.CoopShareTransactionType.TRANSFER_IN,
                ]
            )
            .order_by("valid_at")
            .first()
        )

        if not earliest_transaction:
            return None

        return earliest_transaction.valid_at

    @classmethod
    def can_member_cancel_coop_membership(
        cls, member: Member, reference_date: datetime.date | None = None
    ):
        if reference_date is None:
            reference_date = get_today()

        entry_date = cls.get_coop_entry_date(member)
        return entry_date is not None and entry_date > reference_date

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
