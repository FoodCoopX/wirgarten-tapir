from decimal import Decimal

from tapir.associations.models import AssociationDepositAccount
from tapir.associations.services.association_deposit_balance_calculator import (
    AssociationDepositBalanceCalculator,
)
from tapir.wirgarten.models import Member


class AssociationDepositRemainingAmountCalculator:
    @staticmethod
    def get_remaining_deposit_amount(member: Member, cache: dict) -> Decimal | None:
        account = AssociationDepositAccount.objects.filter(member=member).first()
        if account is None or account.agreed_amount is None:
            return None
        balance = AssociationDepositBalanceCalculator.get_balance(member, cache)
        return max(Decimal("0.00"), account.agreed_amount - balance["retained_amount"])
