from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from tapir.accounts.models import TapirUser
from tapir.associations.models import AssociationDeposit, AssociationMembership
from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today, legal_status_is_association


class AssociationDepositMemberService:
    @staticmethod
    def get_amount(deposit: AssociationDeposit | None) -> Decimal:
        if deposit is None:
            return Decimal("0")
        payments = deposit.payments.aggregate(
            amount=Sum("amount", default=Decimal("0"))
        )["amount"]
        return (
            payments
            + (deposit.opening_balance or Decimal("0"))
            + (deposit.imported_outstanding_amount or Decimal("0"))
        )

    @classmethod
    def get_details(cls, member: Member, cache: dict) -> dict:
        settings = AssociationDepositPolicy.get_settings(cache)
        if not legal_status_is_association(cache=cache):
            return {
                "visible": False,
                "name": settings["name"],
                "amount": 0,
                "agreement_requested": False,
                "can_increase": False,
                "minimum": settings["minimum"],
                "increment": settings["increment"],
            }
        deposit = getattr(member, "association_deposit", None)
        amount = cls.get_amount(deposit)
        return {
            "visible": settings["enabled"] or deposit is not None,
            "name": settings["name"],
            "amount": amount,
            "agreement_requested": bool(
                deposit
                and deposit.opening_balance is None
                and not deposit.payments.exists()
            ),
            "can_increase": bool(
                amount
                and not deposit.imported_outstanding_amount
                and AssociationMembership.objects.filter(member=member)
                .active_at(get_today(cache=cache))
                .exists()
                and settings["enabled"]
                and get_parameter_value(
                    ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, cache=cache
                )
            ),
            "minimum": settings["minimum"],
            "increment": settings["increment"],
        }

    @classmethod
    def validate_increase(
        cls,
        member: Member,
        total_amount: Decimal,
        previous_amount: Decimal,
        cache: dict,
    ) -> Decimal:
        settings = AssociationDepositPolicy.get_settings(cache)
        if not settings["enabled"] or not get_parameter_value(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, cache=cache
        ):
            raise ValidationError("Einlagenerhöhungen sind nicht aktiviert.")
        deposit = getattr(member, "association_deposit", None)
        today = get_today(cache=cache)
        if (
            not AssociationMembership.objects.filter(member=member)
            .active_at(today)
            .exists()
        ):
            raise ValidationError("Eine aktive Vereinsmitgliedschaft ist erforderlich.")
        current = cls.get_amount(deposit)
        if current <= 0 or total_amount < current:
            raise ValidationError(
                "Eine bestehende Einlage kann hier nur erhöht werden."
            )
        if deposit.imported_outstanding_amount:
            raise ValidationError(
                "Bitte kläre den importierten offenen Betrag mit der Verwaltung."
            )
        if total_amount == current:
            return Decimal("0")
        if current != previous_amount:
            raise ValidationError(
                "Die Einlage hat sich geändert. Bitte lade die Seite neu."
            )
        AssociationDepositAmountValidator.validate_regular_deposit_amount(
            amount=total_amount, cache=cache
        )
        amount = total_amount - current
        AssociationDepositPaymentCreator.validate_debit(
            member=member, amount=amount, cache=cache
        )
        return amount

    @staticmethod
    @transaction.atomic
    def increase(
        member: Member, amount: Decimal, actor: TapirUser, cache: dict
    ) -> None:
        AssociationDepositPaymentCreator.create_deposit_payment(
            deposit=member.association_deposit,
            amount=amount,
            earliest_date=get_today(cache=cache),
            actor=actor,
            cache=cache,
        )
