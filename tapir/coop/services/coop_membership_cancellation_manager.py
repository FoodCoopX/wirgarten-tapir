import datetime
from decimal import Decimal

from tapir.accounts.models import TapirUser
from tapir.coop.models import (
    CoopSharesCancelledDuringTrialLogEntry,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, CoopShareTransaction
from tapir.wirgarten.utils import get_today


class CoopMembershipCancellationManager:
    @classmethod
    def get_coop_entry_date(cls, member: Member, cache: dict):
        member_transactions = TapirCache.get_coop_share_transaction_by_member_id(
            cache=cache, member_id=member.id
        )
        for transaction in member_transactions:
            if transaction.transaction_type in [
                CoopShareTransaction.CoopShareTransactionType.PURCHASE,
                CoopShareTransaction.CoopShareTransactionType.TRANSFER_IN,
            ]:
                return transaction.valid_at

        return None

    @classmethod
    def can_member_cancel_coop_membership(
        cls,
        member: Member,
        reference_date: datetime.date,
        cache: dict,
    ):
        entry_date = cls.get_coop_entry_date(member, cache=cache)
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
            CoopSharesCancelledDuringTrialLogEntry.populate_transaction(
                coop_share_transaction=purchase,
                user=member,
                actor=actor,
            ).save()

        future_coop_share_purchases.delete()

    @classmethod
    def is_in_coop_trial(cls, member: Member, cache: dict):
        entry_date = cls.get_coop_entry_date(member, cache)
        return entry_date is not None and entry_date > get_today()
