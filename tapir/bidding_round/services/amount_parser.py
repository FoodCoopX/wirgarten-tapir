from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class AmountParser:
    """Parses user-entered amounts, shared by round prices and bids.

    The amount inputs accept a decimal comma and a currency symbol, so the API
    cannot use a plain ``Decimal`` field."""

    @classmethod
    def parse_optional(cls, value) -> Decimal | None:
        if value in (None, ""):
            return None
        return cls.parse_decimal(value)

    @classmethod
    def parse_decimal(cls, value) -> Decimal:
        if isinstance(value, str):
            value = value.strip().replace("€", "").replace(",", ".")
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            raise ValidationError(_("Bitte gib eine gültige Zahl ein."))
