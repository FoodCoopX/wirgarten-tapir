import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError

from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.payments.services.payment_due_date_calculator import PaymentDueDateCalculator


class AssociationDepositInstalmentCalculator:
    @staticmethod
    def build_payment_schedule(
        amount: Decimal, count: int, earliest_date: datetime.date, cache: dict
    ) -> list[dict]:
        AssociationDepositAmountValidator.validate_positive_amount(amount)
        cents = int(amount * 100)
        if type(count) is not int or count < 1 or count > cents:
            raise ValidationError(
                "Die Ratenzahl muss positiv sein und jede Rate mindestens einen Cent betragen."
            )
        base, remainder = divmod(cents, count)
        first_due = PaymentDueDateCalculator.get_first_due_date_on_or_after(
            earliest_date, cache
        )
        return [
            {
                "amount": (Decimal(base + (index < remainder)) / 100).quantize(
                    Decimal("0.01")
                ),
                "due_date": PaymentDueDateCalculator.get_first_due_date_on_or_after(
                    first_due.replace(day=1) + relativedelta(months=index), cache
                ),
                "instalment_number": index + 1 if count > 1 else None,
            }
            for index in range(count)
        ]
