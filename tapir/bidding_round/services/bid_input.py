from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import BIDDING_ROUND_MIN_SHARES
from tapir.bidding_round.services.amount_parser import AmountParser


@dataclass(frozen=True)
class BidInput:
    """One typed bid: a product, a number of shares and the monthly amount per share.

    The view, the validator and ``save_bid`` pass this object around instead of a
    mapping, so the values are converted once and never mutated in place.
    """

    product_id: str
    quantity: int
    amount_1: Decimal

    @classmethod
    def from_mapping(cls, payload: dict) -> "BidInput":
        amount_1 = AmountParser.parse_optional(payload.get("amount_1"))
        if amount_1 is None:
            raise ValidationError(_("Bitte gib einen Betrag an."))
        return cls(
            product_id=str(payload.get("product_id") or ""),
            quantity=cls._to_int(payload.get("quantity")),
            amount_1=amount_1,
        )

    @staticmethod
    def _to_int(value) -> int:
        if value in (None, ""):
            return BIDDING_ROUND_MIN_SHARES
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError(
                _("Bitte gib die Anzahl der Anteile als ganze Zahl an.")
            )
