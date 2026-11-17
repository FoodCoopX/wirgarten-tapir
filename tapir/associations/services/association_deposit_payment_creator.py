import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDeposit,
    AssociationDepositAgreedLogEntry,
)
from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.associations.services.association_deposit_settings import (
    association_deposits_enabled,
)
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.payments.services.payment_due_date_calculator import PaymentDueDateCalculator
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.utils import get_now


class AssociationDepositPaymentCreator:
    @staticmethod
    def validate_new_deposit(member: Member, amount: Decimal, cache: dict):
        if not association_deposits_enabled(cache):
            raise ValidationError("Vereinseinlagen sind nicht aktiviert.")
        if AssociationDeposit.objects.filter(member=member).exists():
            raise ValidationError(
                "Für dieses Mitglied wurde bereits eine Einlage vereinbart."
            )
        AssociationDepositPaymentCreator.validate_debit(
            member=member, amount=amount, cache=cache
        )

    @staticmethod
    def validate_debit(member: Member, amount: Decimal, cache: dict):
        AssociationDepositAmountValidator.validate_positive_amount(amount)
        if member.sepa_consent is None or member.sepa_consent > get_now(cache=cache):
            raise ValidationError(
                "Für den Einzug ist eine gültige SEPA-Zustimmung erforderlich."
            )

    @staticmethod
    @transaction.atomic
    def create_deposit_and_payment(
        member: Member,
        amount: Decimal,
        start_date: datetime.date,
        actor: TapirUser | None,
        cache: dict,
    ) -> Payment:
        deposit = AssociationDeposit.objects.create(member=member)
        return AssociationDepositPaymentCreator.create_deposit_payment(
            deposit=deposit,
            amount=amount,
            earliest_date=start_date,
            actor=actor,
            cache=cache,
        )

    @staticmethod
    def create_deposit_payment(
        deposit: AssociationDeposit,
        amount: Decimal,
        earliest_date: datetime.date,
        actor: TapirUser | None,
        cache: dict,
    ) -> Payment:
        member = deposit.member
        mandate = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache=cache
        )
        due_date = PaymentDueDateCalculator.get_first_due_date_on_or_after(
            earliest_date=earliest_date, cache=cache
        )
        payment = Payment.objects.create(
            association_deposit=deposit,
            due_date=due_date,
            mandate_ref=mandate,
            amount=amount,
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
        )
        AssociationDepositAgreedLogEntry(amount=amount).populate(
            actor=actor, user=member
        ).save()
        return payment
