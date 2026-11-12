from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import DecimalValidator, MinValueValidator

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import format_currency


class AssociationDepositAmountValidator:
    @staticmethod
    def validate_positive_amount(amount: Decimal):
        DecimalValidator(max_digits=8, decimal_places=2)(amount)
        MinValueValidator(Decimal("0.01"))(amount)

    @staticmethod
    def validate_regular_deposit_amount(amount: Decimal, cache: dict):
        DecimalValidator(max_digits=8, decimal_places=2)(amount)
        minimum = Decimal(
            str(
                get_parameter_value(
                    ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, cache=cache
                )
            )
        )
        increment = Decimal(
            str(
                get_parameter_value(
                    ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT, cache=cache
                )
            )
        )
        if amount < minimum:
            raise ValidationError(
                f"Die Mindesteinlage beträgt {format_currency(minimum)} €."
            )
        if (amount - minimum) % increment != 0:
            raise ValidationError(
                f"Bitte Schritte von {format_currency(increment)} € ab der Mindesteinlage verwenden."
            )
