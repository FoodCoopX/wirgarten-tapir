from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import (
    BIDDING_ROUND_MAX_SHARES,
    BIDDING_ROUND_MIN_SHARES,
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_STATUS_ACTIVE,
)
from tapir.bidding_round.models import BiddingRound, BiddingRoundProductPrice
from tapir.bidding_round.services.bid_input import BidInput
from tapir.wirgarten.models import Product
from tapir.wirgarten.utils import get_now


class BidValidator:
    """Validates one bid against the round and returns the validated input.

    It works on ``BidInput``, so the API and a management command share the same
    checks without a serializer in between.
    """

    AMOUNT_LEVELS = (1, 2, 3)

    @classmethod
    def validate(
        cls, bidding_round: BiddingRound, bid_input: BidInput, cache: dict
    ) -> BidInput:
        cls._validate_round_is_open(bidding_round, cache)
        product = cls._get_product(bidding_round, bid_input.product_id)
        price = cls._get_price_row(bidding_round, product)
        quantity = cls._validate_quantity(bid_input.quantity)
        amounts = cls._validate_amounts(bidding_round, bid_input, price, product)
        return BidInput(
            product_id=product.id,
            quantity=quantity,
            amount_1=amounts[1],
            amount_2=amounts[2],
            amount_3=amounts[3],
        )

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
    def _get_price_row(
        cls, bidding_round: BiddingRound, product: Product
    ) -> BiddingRoundProductPrice:
        price = bidding_round.prices.filter(product=product).first()
        if price is None:
            raise ValidationError(
                _(
                    "Für dieses Produkt ist in dieser Beitragsrunde kein Preis hinterlegt."
                )
            )
        return price

    @classmethod
    def _validate_quantity(cls, quantity: int) -> int:
        if not BIDDING_ROUND_MIN_SHARES <= quantity <= BIDDING_ROUND_MAX_SHARES:
            raise ValidationError(cls._quantity_error())
        return quantity

    @classmethod
    def _quantity_error(cls) -> str:
        return _("Bitte gib zwischen %(min)s und %(max)s Anteile an.") % {
            "min": BIDDING_ROUND_MIN_SHARES,
            "max": BIDDING_ROUND_MAX_SHARES,
        }

    @classmethod
    def _validate_amounts(
        cls,
        bidding_round: BiddingRound,
        bid_input: BidInput,
        price: BiddingRoundProductPrice,
        product: Product,
    ) -> dict:
        amounts = {
            1: bid_input.amount_1,
            2: bid_input.amount_2,
            3: bid_input.amount_3,
        }
        cls._validate_levels(bidding_round, amounts)

        for amount in amounts.values():
            if amount is None:
                continue
            if not amount.is_finite() or amount <= 0:
                raise ValidationError(_("Der Betrag muss größer als 0 sein."))
            if price.min_amount is not None and amount < price.min_amount:
                raise ValidationError(
                    _(
                        "Der Betrag für %(product)s muss mindestens %(min_amount)s € betragen."
                    )
                    % {"product": product.name, "min_amount": price.min_amount}
                )
        return amounts

    @classmethod
    def _validate_levels(cls, bidding_round: BiddingRound, amounts: dict) -> None:
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            if amounts[1] is None or amounts[2] is None:
                raise ValidationError(_("Bitte den Grün- und den Rot-Betrag angeben."))
            if amounts[3] is not None:
                raise ValidationError(_("Es wurden zu viele Gebote angegeben."))
        else:
            required_levels = max(1, min(3, bidding_round.bid_levels))
            for level in range(1, required_levels + 1):
                if amounts[level] is None:
                    raise ValidationError(_("Bitte alle Gebote angeben."))
            for level in range(required_levels + 1, 4):
                if amounts[level] is not None:
                    raise ValidationError(_("Es wurden zu viele Gebote angegeben."))

        provided = [
            amounts[level] for level in cls.AMOUNT_LEVELS if amounts[level] is not None
        ]
        for first, second in zip(provided, provided[1:]):
            if first > second:
                raise ValidationError(_("Die Gebote müssen aufsteigend sein."))
