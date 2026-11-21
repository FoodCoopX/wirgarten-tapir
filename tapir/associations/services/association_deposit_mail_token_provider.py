from tapir.associations.mail_tokens import ASSOCIATION_DEPOSIT_AMOUNT_TOKEN
from tapir.associations.services.association_deposit_member_service import (
    AssociationDepositMemberService,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import format_currency, legal_status_is_association


class AssociationDepositMailTokenProvider:
    @staticmethod
    def build_tokens(member: Member, cache: dict) -> dict[str, str]:
        if not legal_status_is_association(cache=cache):
            return {ASSOCIATION_DEPOSIT_AMOUNT_TOKEN: ""}
        amount = AssociationDepositMemberService.get_amount(
            getattr(member, "association_deposit", None)
        )
        return {
            ASSOCIATION_DEPOSIT_AMOUNT_TOKEN: format_currency(amount) if amount else ""
        }
