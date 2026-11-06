from tapir.associations.mail_tokens import ASSOCIATION_DEPOSIT_MAIL_TOKENS
from tapir.associations.models import AssociationDepositAccount
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.associations.services.association_deposit_overview_provider import (
    AssociationDepositOverviewProvider,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.utils import (
    format_currency,
    format_date,
    legal_status_is_association,
)


class AssociationDepositMailTokenProvider:
    @classmethod
    def build_tokens(cls, member: Member, cache: dict) -> dict:
        empty = dict.fromkeys(ASSOCIATION_DEPOSIT_MAIL_TOKENS.values(), "")
        if not legal_status_is_association(cache=cache):
            return empty
        if not AssociationDepositAccount.objects.filter(member=member).exists():
            return empty
        details = AssociationDepositDetailsProvider.get_deposit_details(member, cache)
        return {
            "association_deposit_name": AssociationDepositPolicy.get_settings(cache)[
                "name"
            ],
            "association_deposit_amount": (
                "Nicht vereinbart"
                if details["agreed_amount"] is None
                else format_currency(details["agreed_amount"])
            ),
            "association_deposit_status": AssociationDepositOverviewProvider.STATES[
                details["state"]
            ],
            "association_deposit_payment_plan": "; ".join(
                cls._format_payment(payment) for payment in details["payments"]
            )
            or "Kein Einzug vereinbart",
            "association_deposit_retained_amount": format_currency(
                details["retained_amount"]
            ),
            "association_deposit_refunded_amount": format_currency(
                details["refunded_amount"]
            ),
        }

    @staticmethod
    def _format_payment(payment: dict) -> str:
        state = "offen"
        if (
            payment["transaction_id"] is not None
            or payment["status"] == Payment.PaymentStatus.PAID
        ):
            state = "verbucht/exportiert"
        elif payment["status"] == "STOPPED":
            state = "Einzug gesperrt"
        return f'{format_date(payment["due_date"])}: {format_currency(payment["amount"])} € ({state})'
