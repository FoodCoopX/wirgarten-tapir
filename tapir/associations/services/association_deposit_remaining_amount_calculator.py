from decimal import Decimal

from django.db.models import Q, Sum

from tapir.associations.models import AssociationDepositAccount
from tapir.associations.services.association_deposit_receipt_total_calculator import (
    AssociationDepositReceiptTotalCalculator,
)
from tapir.wirgarten.models import Member, Payment


class AssociationDepositRemainingAmountCalculator:
    @staticmethod
    def get_remaining_deposit_amount(member: Member, cache: dict) -> Decimal | None:
        account = AssociationDepositAccount.objects.filter(member=member).first()
        if account is None or account.agreed_amount is None:
            return None
        received = AssociationDepositReceiptTotalCalculator.get_received_deposit_total(
            member=member, cache=cache
        )
        committed = account.payments.filter(
            Q(transaction__isnull=False) | Q(status=Payment.PaymentStatus.PAID)
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        return max(Decimal("0.00"), account.agreed_amount - received - committed)
