from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.associations.models import AssociationDeposit
from tapir.associations.services.association_deposit_service import (
    AssociationDepositService,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import format_currency


class DepositMailService:
    PENDING_AGREEMENT_TRIGGER = "associations.deposit_agreement_pending"

    @classmethod
    def amount_token(cls, recipient, cache: dict):
        if not isinstance(recipient, Member):
            return ""
        deposit = AssociationDeposit.objects.filter(member=recipient).first()
        if deposit is None:
            return ""
        if deposit.agreed_amount is None and not deposit.cancellation_date:
            return "Individuelle Vereinbarung offen"
        if deposit.agreed_amount is None:
            return "Keine Einlage vereinbart"
        return format_currency(deposit.agreed_amount) + " €"

    @classmethod
    def balance_token(cls, recipient, cache: dict):
        if not isinstance(recipient, Member):
            return ""
        deposit = AssociationDeposit.objects.filter(member=recipient).first()
        return (
            format_currency(
                AssociationDepositService.balances(deposit, cache)["balance"]
            )
            + " €"
            if deposit
            else ""
        )

    @classmethod
    def notify_pending_agreement(cls, member: Member, cache: dict):
        email = get_parameter_value(ParameterKeys.SITE_ADMIN_EMAIL, cache=cache)
        if not email:
            return
        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=cls.PENDING_AGREEMENT_TRIGGER,
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email=email,
                    first_name=get_parameter_value(
                        ParameterKeys.SITE_ADMIN_NAME, cache=cache
                    ),
                    last_name="",
                ),
                token_data={
                    "deposit_member_name": f"{member.first_name} {member.last_name}",
                    "deposit_member_number": str(member.member_no),
                    "deposit_member_email": member.email,
                    "deposit_status": "Individuelle Vereinbarung offen",
                },
            )
        )
