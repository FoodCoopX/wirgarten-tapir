from django.db.models import Q, F

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositAgreementAuthorizedLogEntry,
)
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today


class AssociationDepositAdministrationProvider:
    @staticmethod
    def get_accounts(include_closed: bool, cache: dict):
        accounts = AssociationDepositAccount.objects.select_related("member")
        if not include_closed:
            accounts = accounts.filter(
                Q(hardship_requested_at__isnull=False, agreed_amount=None)
                | Q(refund_requires_agreement=True, agreed_amount__gt=0)
                | (
                    Q(collection_stopped_from__isnull=False)
                    & (
                        Q(member__associationmembership__end_date__isnull=True)
                        | Q(
                            member__associationmembership__end_date__gte=F(
                                "collection_stopped_from"
                            )
                        )
                    )
                )
            ).filter(
                Q(refund_requires_agreement=False)
                | (
                    Q(member__associationmembership__isnull=False)
                    & (
                        Q(member__associationmembership__end_date__isnull=True)
                        | Q(
                            member__associationmembership__end_date__gte=get_today(
                                cache
                            )
                        )
                    )
                )
            )
        return accounts.distinct().order_by("hardship_requested_at", "pk")

    @staticmethod
    def get_case(member: Member, cache: dict) -> dict:
        account = AssociationDepositAccount.objects.filter(member=member).first()
        details = AssociationDepositDetailsProvider.get_deposit_details(member, cache)
        return {
            "member": member,
            "account": account,
            "details": details,
            "payments": details["payments"],
            "receipts": (
                account.receipts.order_by("received_on", "pk") if account else []
            ),
            "refunds": account.refunds.order_by("refunded_on", "pk") if account else [],
            "agreements": AssociationDepositAgreementAuthorizedLogEntry.objects.filter(
                user=member
            ).order_by("-created_date"),
        }
