from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import (
    BIDDING_ROUND_MAX_SHARES,
    BIDDING_ROUND_MIN_SHARES,
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
        amount = cls._parse_amount(item.get("amount_1"))
        min_amount = cls._get_min_amount(round_product_type, product)
        if min_amount is not None and amount < min_amount:
            raise ValidationError(
                _(
                    "Der Betrag für %(product)s muss mindestens %(min_amount)s € betragen."
                )
                % {"product": product.name, "min_amount": min_amount}
            )
        item["quantity"] = quantity
        item["amount_1"] = amount
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
    def _parse_amount(cls, value) -> Decimal:
        if value in (None, ""):
            raise ValidationError(_("Bitte gib einen Betrag an."))
        amount = AmountParser.parse_decimal(value)
        if not amount.is_finite() or amount <= 0:
            raise ValidationError(_("Der Betrag muss größer als 0 sein."))
        return amount

    @classmethod
    def _get_min_amount(cls, round_product_type, product):
        price = round_product_type.prices.filter(product=product).first()
        return price.min_amount if price is not None else None
