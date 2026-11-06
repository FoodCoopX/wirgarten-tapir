from decimal import Decimal

from django.db.models import Q, Sum

from tapir.associations.models import AssociationDepositRefund
from tapir.associations.services.association_deposit_receipt_total_calculator import (
    AssociationDepositReceiptTotalCalculator,
)
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.utils import get_today


class AssociationDepositBalanceCalculator:
    @staticmethod
    def get_balance(member: Member, cache: dict) -> dict:
        received = AssociationDepositReceiptTotalCalculator.get_received_deposit_total(
            member, cache
        )
        committed = Payment.objects.filter(
            association_deposit_account__member=member
        ).filter(
            Q(transaction__isnull=False) | Q(status=Payment.PaymentStatus.PAID)
        ).aggregate(
            total=Sum("amount")
        )[
            "total"
        ] or Decimal(
            "0"
        )
        refunded = AssociationDepositRefund.objects.filter(
            account__member=member, refunded_on__lte=get_today(cache)
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        return AssociationDepositBalanceCalculator.from_totals(
            received, committed, refunded
        )

    @staticmethod
    def from_totals(received: Decimal, committed: Decimal, refunded: Decimal) -> dict:
        return {
            "received_amount": received,
            "committed_amount": committed,
            "refunded_amount": refunded,
            "retained_amount": received + committed - refunded,
        }
