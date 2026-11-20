from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import (
    BIDDING_ROUND_MAX_SHARES,
    BIDDING_ROUND_MIN_SHARES,
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_STATUS_ACTIVE,
)
from tapir.bidding_round.models import BiddingRoundProductType
from tapir.bidding_round.services.amount_parser import AmountParser
from tapir.wirgarten.models import Product
from tapir.wirgarten.utils import get_now


class BidValidator:
    @classmethod
    def validate(cls, bidding_round, items, cache):
        cls._validate_round_is_open(bidding_round, cache)
        if not items:
            raise ValidationError(_("Bitte gib einen Betrag für deinen Anteil an."))

        seen_products = set()
        for item in items:
            product_id = cls._validate_item(bidding_round, item)
            if product_id in seen_products:
                raise ValidationError(
                    _("Jedes Produkt darf nur einmal im Gebot vorkommen.")
                )
            seen_products.add(product_id)

    @classmethod
    def _validate_round_is_open(cls, bidding_round, cache):
        if bidding_round.status != BIDDING_ROUND_STATUS_ACTIVE:
            raise ValidationError(_("Die Beitragsrunde ist nicht aktiv."))
        if bidding_round.contracts_created_at is not None:
            raise ValidationError(
                _("Die Beitragsrunde ist bereits abgeschlossen und ausgewertet.")
            )
        now = get_now(cache=cache)
        if bidding_round.start_at is not None and now < bidding_round.start_at:
            raise ValidationError(_("Die Beitragsrunde hat noch nicht begonnen."))
        if now > bidding_round.end_at:
            raise ValidationError(_("Die Beitragsrunde ist bereits beendet."))

    @classmethod
    def _validate_item(cls, bidding_round, item) -> str:
        round_product_type = cls._get_round_product_type(bidding_round, item)
        product = cls._get_product(round_product_type, item)
        quantity = cls._parse_quantity(item.get("quantity"))
        amounts = cls._parse_amounts(item)
        cls._validate_levels(bidding_round, amounts)

        min_amount = cls._get_min_amount(round_product_type, product)
        for amount in amounts.values():
            if amount is None:
                continue
            if amount <= 0:
                raise ValidationError(_("Der Betrag muss größer als 0 sein."))
            if min_amount is not None and amount < min_amount:
                raise ValidationError(
                    _(
                        "Der Betrag für %(product)s muss mindestens %(min_amount)s € betragen."
                    )
                    % {"product": product.name, "min_amount": min_amount}
                )

        item["quantity"] = quantity

        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            amounts[3] = None
        for level in (1, 2, 3):
            item[f"amount_{level}"] = amounts[level]
        item["product_id"] = product.id
        item["round_product_type_id"] = round_product_type.id
        return product.id

    @classmethod
    def _get_round_product_type(cls, bidding_round, item):
        round_product_type = BiddingRoundProductType.objects.filter(
            id=item.get("round_product_type_id"), round=bidding_round
        ).first()
        if round_product_type is None:
            raise ValidationError(
                _("Das Produkt gehört nicht zu dieser Beitragsrunde.")
            )
        return round_product_type

    @classmethod
    def _get_product(cls, round_product_type, item) -> Product:
        product = Product.objects.filter(id=item.get("product_id")).first()
        if product is None or product.type_id != round_product_type.product_type_id:
            raise ValidationError(
                _("Das Produkt gehört nicht zum Produkttyp dieser Beitragsrunde.")
            )
        return product

    @classmethod
    def _parse_quantity(cls, value) -> int:
        if value in (None, ""):
            return BIDDING_ROUND_MIN_SHARES
        if isinstance(value, bool):
            raise ValidationError(cls._quantity_error())
        try:
            quantity = int(value)
        except (TypeError, ValueError):
            raise ValidationError(cls._quantity_error())
        if isinstance(value, float) and not value.is_integer():
            raise ValidationError(cls._quantity_error())
        if isinstance(value, Decimal) and value != quantity:
            raise ValidationError(cls._quantity_error())
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
    def _parse_amounts(cls, item) -> dict:
        amounts = {}
        for level in (1, 2, 3):
            amount = AmountParser.parse_optional(item.get(f"amount_{level}"))
            if amount is not None and not amount.is_finite():
                raise ValidationError(_("Bitte gib eine gültige Zahl ein."))
            amounts[level] = amount
        return amounts

    @classmethod
    def _validate_levels(cls, bidding_round, amounts: dict):
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            cls._validate_bid_range_levels(amounts)
        else:
            cls._validate_simple_levels(bidding_round, amounts)
        cls._validate_levels_are_ascending(amounts)

    @classmethod
    def _validate_bid_range_levels(cls, amounts: dict):
        if amounts[1] is None or amounts[2] is None:
            raise ValidationError(_("Bitte den Grün- und den Rot-Betrag angeben."))
        if amounts[3] is not None:
            raise ValidationError(_("Es wurden zu viele Gebote angegeben."))

    @classmethod
    def _validate_simple_levels(cls, bidding_round, amounts: dict):
        required_levels = max(1, min(3, bidding_round.bid_levels))
        for level in range(1, required_levels + 1):
            if amounts[level] is None:
                raise ValidationError(_("Bitte alle Gebote angeben."))
        for level in range(required_levels + 1, 4):
            if amounts[level] is not None:
                raise ValidationError(_("Es wurden zu viele Gebote angegeben."))

    @classmethod
    def _validate_levels_are_ascending(cls, amounts: dict):
        provided = [amounts[level] for level in (1, 2, 3) if amounts[level] is not None]
        for first, second in zip(provided, provided[1:]):
            if first > second:
                raise ValidationError(_("Die Gebote müssen aufsteigend sein."))

    @classmethod
    def _get_min_amount(cls, round_product_type, product):
        price = round_product_type.prices.filter(product=product).first()
        return price.min_amount if price is not None else None
