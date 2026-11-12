from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDeposit,
    AssociationDepositAgreedLogEntry,
    AssociationMembership,
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
    @transaction.atomic
    def create_payment(
        membership: AssociationMembership,
        amount: Decimal,
        actor: TapirUser | None,
        cache: dict,
    ) -> Payment:
        Member.objects.select_for_update(no_key=True).get(pk=membership.member_id)
        membership = (
            AssociationMembership.objects.select_for_update(of=("self",))
            .select_related("member")
            .get(pk=membership.pk)
        )
        existing = AssociationDeposit.objects.filter(membership=membership).first()
        if existing is not None:
            if existing.payment is None or existing.payment.amount != amount:
                raise ValidationError(
                    "Für diese Mitgliedschaft wurde bereits eine Einlage vereinbart."
                )
            return existing.payment

        return AssociationDepositPaymentCreator.create_agreed_debit(
            membership, amount, actor, cache
        )

    @staticmethod
    def create_agreed_debit(
        membership: AssociationMembership,
        amount: Decimal,
        actor: TapirUser | None,
        cache: dict,
    ) -> Payment:
        if not association_deposits_enabled(cache):
            raise ValidationError("Vereinseinlagen sind nicht aktiviert.")
        AssociationDepositAmountValidator.validate_positive_amount(amount)
        member = membership.member
        now = get_now(cache=cache)
        if member.sepa_consent is None or member.sepa_consent > now:
            raise ValidationError(
                "Für den Einzug ist eine gültige SEPA-Zustimmung erforderlich."
            )

        mandate = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache=cache
        )
        due_date = PaymentDueDateCalculator.get_first_due_date_on_or_after(
            earliest_date=max(
                membership.start_date, now.date(), mandate.start_ts.date()
            ),
            cache=cache,
        )
        if membership.end_date is not None and due_date > membership.end_date:
            raise ValidationError("Die Mitgliedschaft endet vor dem Einzugstermin.")
        payment = Payment.objects.create(
            due_date=due_date,
            mandate_ref=mandate,
            amount=amount,
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
        )
        AssociationDeposit.objects.create(membership=membership, payment=payment)
        AssociationDepositAgreedLogEntry(amount=amount).populate(
            actor=actor, user=member
        ).save()
        return payment
