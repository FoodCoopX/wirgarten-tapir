from tapir.associations.mail_tokens import ASSOCIATION_DEPOSIT_AMOUNT_TOKEN
from tapir.associations.models import AssociationMembership
from tapir.associations.services.association_deposit_member_service import (
    AssociationDepositMemberService,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import format_currency, legal_status_is_association


class AssociationDepositMailTokenProvider:
    @staticmethod
    def build_tokens(
        member: Member, cache: dict, *, membership: AssociationMembership | None = None
    ) -> dict[str, str]:
        if not legal_status_is_association(cache=cache):
            return {ASSOCIATION_DEPOSIT_AMOUNT_TOKEN: ""}
        if membership is None:
            membership = (
                AssociationMembership.objects.filter(member=member)
                .order_by("-start_date", "-pk")
                .first()
            )
        amount = AssociationDepositMemberService.get_amount(membership)
        return {
            ASSOCIATION_DEPOSIT_AMOUNT_TOKEN: format_currency(amount) if amount else ""
        }
