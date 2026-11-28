from decimal import Decimal

from django.db.models import Exists, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce

from tapir.associations.models import AssociationDepositTransaction
from tapir.wirgarten.models import Member, Payment


class AssociationDepositAnnotator:
    @staticmethod
    def annotate_members(members: QuerySet[Member]) -> QuerySet[Member]:
        member_id = OuterRef("pk")
        transactions = AssociationDepositTransaction.objects.filter(member_id=member_id)
        agreed = transactions.values("member").annotate(total=Sum("amount"))
        exported_payment = Payment.objects.filter(
            association_deposit_transaction_id=OuterRef("pk"), transaction__isnull=False
        )
        received = (
            transactions.annotate(exported=Exists(exported_payment))
            .filter(
                ~Q(
                    transaction_type__in=[
                        AssociationDepositTransaction.Type.SUBSCRIPTION,
                        AssociationDepositTransaction.Type.IMPORT_OUTSTANDING,
                    ]
                )
                | Q(exported=True)
            )
            .values("member")
            .annotate(total=Sum("amount"))
        )
        return members.annotate(
            deposit_agreed=Coalesce(Subquery(agreed.values("total")), Decimal("0")),
            deposit_exported=Coalesce(Subquery(received.values("total")), Decimal("0")),
        )
