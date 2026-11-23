from decimal import Decimal

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDeposit,
    AssociationDepositPaymentOption,
    AssociationMembership,
)
from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)


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
            AssociationDeposit.objects.create(member=membership.member)
        elif amount:
            AssociationDepositPaymentCreator.create_deposit_and_payment(
                member=membership.member,
                start_date=membership.start_date,
                amount=amount,
                actor=actor,
                cache=cache,
            )
