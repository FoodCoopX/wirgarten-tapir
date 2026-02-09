import datetime
from decimal import Decimal
from typing import Dict

from tapir.accounts.models import TapirUser
from tapir.coop.models import CoopSharesCancelledLogEntry
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
        cls,
        member: Member,
        reference_date: datetime.date | None = None,
        cache: Dict = None,
    ):
        if reference_date is None:
            reference_date = get_today(cache)

        entry_date = cls.get_coop_entry_date(member)
        return entry_date is not None and entry_date > reference_date

    @staticmethod
    def cancel_coop_membership(
        member: Member,
        reference_date: datetime.date | None = None,
        actor: TapirUser = None,
        cache: dict = None,
    ):
        if reference_date is None:
            reference_date = get_today(cache=cache)

        future_coop_share_purchases = member.coopsharetransaction_set.filter(
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at__gte=reference_date,
        )

        for purchase in future_coop_share_purchases:
            purchase.payment.amount -= purchase.share_price * purchase.quantity
            if purchase.payment.amount <= Decimal(0):
                purchase.payment.delete()
            else:
                purchase.payment.save()

        for purchase in future_coop_share_purchases:
            CoopSharesCancelledLogEntry.populate_transaction(
                coop_share_transaction=purchase,
                user=member,
                actor=actor,
            ).save()

        future_coop_share_purchases.delete()

    @classmethod
    def is_in_coop_trial(cls, member: Member):
        entry_date = cls.get_coop_entry_date(member)
        return entry_date is not None and entry_date > get_today()
