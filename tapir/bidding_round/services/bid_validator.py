from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import (
    BIDDING_ROUND_MAX_SHARES,
    BIDDING_ROUND_MIN_SHARES,
    BIDDING_ROUND_STATUS_ACTIVE,
)
from tapir.bidding_round.models import BiddingRound
from tapir.bidding_round.services.bid_input import BidInput
from tapir.wirgarten.models import Product
from tapir.wirgarten.utils import get_now


class BidValidator:
    """Validates one bid against the round and returns the validated input.

    It works on ``BidInput``, so the API and a management command share the same
    checks without a serializer in between.
    """

    @classmethod
    def validate(
        cls, bidding_round: BiddingRound, bid_input: BidInput, cache: dict
    ) -> BidInput:
        cls._validate_round_is_open(bidding_round, cache)
        product = cls._get_product(bidding_round, bid_input.product_id)
        quantity = cls._validate_quantity(bid_input.quantity)
        amount = cls._validate_amount(bid_input.amount_1)
        cls._validate_min_amount(bidding_round, product, amount)
        return BidInput(product_id=product.id, quantity=quantity, amount_1=amount)

    @classmethod
    def _validate_round_is_open(cls, bidding_round: BiddingRound, cache: dict) -> None:
        if bidding_round.status != BIDDING_ROUND_STATUS_ACTIVE:
            raise ValidationError(_("Die Beitragsrunde ist nicht aktiv."))
        if bidding_round.contracts_created_at is not None:
            raise ValidationError(
                _("Die Beitragsrunde ist bereits abgeschlossen und ausgewertet.")
            )
        now = get_now(cache=cache)
        if now < bidding_round.start_at:
            raise ValidationError(_("Die Beitragsrunde hat noch nicht begonnen."))
        if now > bidding_round.end_at:
            raise ValidationError(_("Die Beitragsrunde ist bereits beendet."))

    @classmethod
    def _get_product(cls, bidding_round: BiddingRound, product_id: str) -> Product:
        product = Product.objects.filter(id=product_id, deleted=False).first()
        if product is None or product.type_id != bidding_round.product_type_id:
            raise ValidationError(
                _("Das Produkt gehört nicht zum Produkttyp dieser Beitragsrunde.")
            )
        return product

    @classmethod
    def _validate_quantity(cls, quantity: int) -> int:
        if not BIDDING_ROUND_MIN_SHARES <= quantity <= BIDDING_ROUND_MAX_SHARES:
            raise ValidationError(cls._quantity_error())
        return quantity

    @classmethod
    def _quantity_error(cls):
        return _("Bitte gib zwischen %(min)s und %(max)s Anteile an.") % {
            "min": BIDDING_ROUND_MIN_SHARES,
            "max": BIDDING_ROUND_MAX_SHARES,
        }

    @classmethod
    def _validate_amount(cls, amount: Decimal) -> Decimal:
        if not isinstance(amount, Decimal) or not amount.is_finite() or amount <= 0:
            raise ValidationError(_("Der Betrag muss größer als 0 sein."))
        return amount

    @classmethod
    def _validate_min_amount(
        cls, bidding_round: BiddingRound, product: Product, amount: Decimal
    ) -> None:
        price = bidding_round.prices.filter(product=product).first()
        if price is None or price.min_amount is None:
            return
        if amount < price.min_amount:
            raise ValidationError(
                _(
                    "Der Betrag für %(product)s muss mindestens %(min_amount)s € betragen."
                )
                % {"product": product.name, "min_amount": price.min_amount}
            )
