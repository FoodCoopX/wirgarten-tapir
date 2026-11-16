from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import BIDDING_ROUND_MIN_SHARES
from tapir.bidding_round.services.amount_parser import AmountParser


@dataclass(frozen=True)
class BidInput:
    """One typed bid: a product, a number of shares and the procedure's amounts.

    The view, the validator and ``save_bid`` pass this object around instead of a
    mapping, so the values are converted once and never mutated in place. Which
    amounts are required depends on the round's procedure; the validator decides that.
    """

    product_id: str
    quantity: int
    amount_1: Decimal | None
    amount_2: Decimal | None = None
    amount_3: Decimal | None = None

    @classmethod
    def from_mapping(cls, payload: dict) -> "BidInput":
        return cls(
            product_id=str(payload.get("product_id") or ""),
            quantity=cls._to_int(payload.get("quantity")),
            amount_1=AmountParser.parse_optional(payload.get("amount_1")),
            amount_2=AmountParser.parse_optional(payload.get("amount_2")),
            amount_3=AmountParser.parse_optional(payload.get("amount_3")),
        )

    @staticmethod
    def _to_int(value: object) -> int:
        if value in (None, ""):
            return BIDDING_ROUND_MIN_SHARES
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError(
                _("Bitte gib die Anzahl der Anteile als ganze Zahl an.")
            )
