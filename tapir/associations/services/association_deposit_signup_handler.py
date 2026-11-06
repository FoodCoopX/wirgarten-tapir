import datetime
from decimal import Decimal

from django.db import transaction

from tapir.accounts.models import TapirUser
from tapir.associations.services.association_deposit_agreement_creator import (
    AssociationDepositAgreementCreator,
)
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.wirgarten.models import Member


class AssociationDepositSignupHandler:
    @staticmethod
    @transaction.atomic
    def create_signup_deposit(
        member: Member,
        amount: Decimal | None,
        effective_from: datetime.date,
        has_products: bool,
        actor: TapirUser | None,
        cache: dict,
    ):
        AssociationDepositPolicy.validate_signup_amount(amount, has_products, cache)
        if not AssociationDepositPolicy.is_enabled(cache) or not amount:
            return
        AssociationDepositAgreementCreator.create_regular_agreement(
            member=member,
            amount=amount,
            effective_from=effective_from,
            actor=actor,
            cache=cache,
        )
        AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            member, actor, cache
        )
