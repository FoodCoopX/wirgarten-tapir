import datetime
from decimal import Decimal

from django.db.models import Sum

from tapir.associations.models import AssociationDepositReceipt
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today


class AssociationDepositReceiptTotalCalculator:
    @staticmethod
    def get_received_deposit_total(
        member: Member, cache: dict, reference_date: datetime.date | None = None
    ) -> Decimal:
        reference_date = reference_date or get_today(cache=cache)
        return AssociationDepositReceipt.objects.filter(
            account__member=member, received_on__lte=reference_date
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
