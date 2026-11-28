from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum

from tapir.associations.models import (
    AssociationDepositTransaction,
    AssociationMembership,
)
from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)
from tapir.associations.services.association_deposit_settings import (
    association_deposits_enabled,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class AssociationDepositMemberService:
    @staticmethod
    def get_amount(member: Member) -> Decimal:
        return AssociationDepositTransaction.objects.filter(member=member).aggregate(
            amount=Sum("amount", default=Decimal("0"))
        )["amount"]

    @classmethod
    def get_details(cls, member: Member, cache: dict) -> dict:
        amount = cls.get_amount(member)
        return {
            "name": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_NAME, cache=cache
            ),
            "amount": amount,
            "agreement_requested": AssociationMembership.objects.filter(
                member=member, deposit_agreement_requested_at__isnull=False
            ).exists(),
            "can_increase": amount > 0
            and association_deposits_enabled(cache)
            and AssociationMembership.objects.filter(member=member)
            .active_at(get_today(cache=cache))
            .exists(),
            "minimum": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, cache=cache
            ),
            "increment": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT, cache=cache
            ),
        }

    @classmethod
    def validate_increase(
        cls, member: Member, total_amount: Decimal, cache: dict
    ) -> Decimal:
        if not association_deposits_enabled(cache):
            raise ValidationError("Vereinseinlagen sind nicht aktiviert.")
        if (
            not AssociationMembership.objects.filter(member=member)
            .active_at(get_today(cache=cache))
            .exists()
        ):
            raise ValidationError("Eine aktive Vereinsmitgliedschaft ist erforderlich.")
        current_amount = cls.get_amount(member)
        if current_amount <= 0 or total_amount <= current_amount:
            raise ValidationError(
                "Eine bestehende Einlage kann hier nur erhöht werden."
            )
        AssociationDepositAmountValidator.validate_regular_deposit_amount(
            amount=total_amount, cache=cache
        )
        increase = total_amount - current_amount
        AssociationDepositPaymentCreator.validate_debit(
            member=member, amount=increase, cache=cache
        )
        return increase
