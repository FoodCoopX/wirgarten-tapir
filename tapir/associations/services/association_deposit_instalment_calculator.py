import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError

from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.payments.services.payment_due_date_calculator import PaymentDueDateCalculator


class AssociationDepositInstalmentCalculator:
    MAX_INSTALMENTS = 120

    @classmethod
    def validate_instalment_count(cls, count: int):
        if type(count) is not int or not 1 <= count <= cls.MAX_INSTALMENTS:
            raise ValidationError(
                f"Bitte eine Ratenzahl zwischen 1 und {cls.MAX_INSTALMENTS} angeben."
            )

    @classmethod
    def validate_payment_schedule_amount(cls, amount: Decimal, count: int):
        cls.validate_instalment_count(count)
        AssociationDepositAmountValidator.validate_positive_amount(amount)
        if count > int(amount * 100):
            raise ValidationError("Jede Rate muss mindestens einen Cent betragen.")

    @staticmethod
    def build_payment_schedule(
        amount: Decimal, count: int, earliest_date: datetime.date, cache: dict
    ) -> list[dict]:
        AssociationDepositInstalmentCalculator.validate_payment_schedule_amount(
            amount, count
        )
        cents = int(amount * 100)
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
