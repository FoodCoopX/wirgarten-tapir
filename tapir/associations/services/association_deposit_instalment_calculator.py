import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError

from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.payments.services.payment_due_date_calculator import PaymentDueDateCalculator
from tapir.wirgarten.models import Payment


class AssociationDepositInstalmentCalculator:
    MAX_INSTALMENTS = 12

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
    def adjust_open_payments(
        amount: Decimal, count: int, payments: list[Payment], allow_increase: bool
    ) -> list[dict]:
        if count == 1 and len(payments) > 1:
            raise ValidationError(
                "Es bestehen mehrere offene Zahlungen ohne Ratenvereinbarung."
            )
        if amount == 0:
            return []
        schedule = [
            {
                "id": p.pk,
                "amount": p.amount,
                "due_date": p.due_date,
                "instalment_number": p.instalment_number,
            }
            for p in payments
        ]
        difference = amount - sum(p["amount"] for p in schedule)
        if difference > 0:
            if count != 1 and not allow_increase:
                raise ValidationError(
                    "Der offene Ratenplan muss ausdrücklich neu vereinbart werden."
                )
            base, extra = divmod(int(difference * 100), len(schedule))
            for index, rate in enumerate(schedule):
                rate["amount"] += Decimal(base + (index < extra)) / 100
        else:
            credit = -difference
            for rate in schedule:
                applied = min(rate["amount"], credit)
                rate["amount"] -= applied
                credit -= applied
        return [rate for rate in schedule if rate["amount"] > 0]

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
