from decimal import Decimal

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationMembershipUpdatedLogEntry,
    AssociationDepositPaymentOption,
    AssociationMembership,
)
from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)

from tapir.log.util import freeze_for_log
from tapir.wirgarten.utils import get_now


class AssociationDepositSignupHandler:
    @staticmethod
    def create_signup_deposit(
        membership: AssociationMembership,
        amount: Decimal,
        payment_option: str,
        actor: TapirUser | None,
        cache: dict,
    ) -> None:
        if payment_option == AssociationDepositPaymentOption.INDIVIDUAL_AGREEMENT:
            before_changes = freeze_for_log(membership)
            membership.deposit_agreement_requested_at = get_now(cache=cache)
            membership.save(update_fields=["deposit_agreement_requested_at"])
            AssociationMembershipUpdatedLogEntry().populate(
                old_frozen=before_changes,
                new_model=membership,
                actor=actor,
                user=membership.member,
            ).save()
        elif amount:
            AssociationDepositPaymentCreator.create_deposit_and_payment(
                member=membership.member,
                start_date=membership.start_date,
                amount=amount,
                actor=actor,
                cache=cache,
            )
