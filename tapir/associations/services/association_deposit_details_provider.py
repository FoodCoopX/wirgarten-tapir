from decimal import Decimal

from django.db.models import Q, Sum

from tapir.associations.models import AssociationDepositAccount, AssociationMembership
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.associations.services.association_deposit_receipt_total_calculator import (
    AssociationDepositReceiptTotalCalculator,
)
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.utils import get_today


class AssociationDepositDetailsProvider:
    @staticmethod
    def get_deposit_details(member: Member, cache: dict) -> dict:
        settings = AssociationDepositPolicy.get_settings(cache)
        account = AssociationDepositAccount.objects.filter(member=member).first()
        agreed = account.agreed_amount if account else None
        committed = pending = Decimal("0")
        if account:
            committed = account.payments.filter(
                Q(transaction__isnull=False) | Q(status=Payment.PaymentStatus.PAID)
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            pending = account.payments.filter(
                transaction=None, status=Payment.PaymentStatus.DUE
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        has_membership = (
            AssociationMembership.objects.filter(member=member)
            .filter(Q(end_date=None) | Q(end_date__gte=get_today(cache)))
            .exists()
        )
        return {
            "settings": settings,
            "visible": settings["enabled"] or account is not None,
            "agreed_amount": agreed,
            "received_amount": AssociationDepositReceiptTotalCalculator.get_received_deposit_total(
                member, cache
            ),
            "committed_amount": committed,
            "pending_amount": pending,
            "can_increase": AssociationDepositPolicy.can_member_increase(account, cache)
            and has_membership,
        }
