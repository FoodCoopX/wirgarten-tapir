from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositAgreementAuthorizedLogEntry,
)
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.wirgarten.models import Member


class AssociationDepositAdministrationProvider:
    @staticmethod
    def get_accounts(include_closed: bool, cache: dict):
        accounts = AssociationDepositAccount.objects.select_related("member")
        if not include_closed:
            accounts = accounts.filter(
                hardship_requested_at__isnull=False, agreed_amount=None
            )
        return accounts.order_by("hardship_requested_at", "pk")

    @staticmethod
    def get_case(member: Member, cache: dict) -> dict:
        account = AssociationDepositAccount.objects.filter(member=member).first()
        return {
            "member": member,
            "account": account,
            "details": AssociationDepositDetailsProvider.get_deposit_details(
                member, cache
            ),
            "payments": account.payments.order_by("due_date", "pk") if account else [],
            "receipts": (
                account.receipts.order_by("received_on", "pk") if account else []
            ),
            "agreements": AssociationDepositAgreementAuthorizedLogEntry.objects.filter(
                user=member
            ).order_by("-created_date"),
        }
