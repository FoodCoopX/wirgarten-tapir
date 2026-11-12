from decimal import Decimal

from tapir.accounts.models import TapirUser
from tapir.associations.models import AssociationDeposit, AssociationMembership
from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)


class AssociationDepositSignupHandler:
    @staticmethod
    def create_signup_deposit(
        *,
        membership: AssociationMembership,
        amount: Decimal | None,
        has_products: bool,
        payment_option: str,
        actor: TapirUser | None,
        cache: dict,
    ):
        AssociationDepositPolicy.validate_signup_selection(
            amount, has_products, cache, payment_option=payment_option
        )
        if payment_option == "individual_agreement":
            AssociationDeposit.objects.get_or_create(member=membership.member)
        elif amount:
            AssociationDepositPaymentCreator.validate_new_deposit(
                member=membership.member, amount=amount, cache=cache
            )
            AssociationDepositPaymentCreator.create_deposit_and_payment(
                member=membership.member,
                start_date=membership.start_date,
                amount=amount,
                actor=actor,
                cache=cache,
            )
