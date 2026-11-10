from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import ACTIVE, TRAFFIC_LIGHT
from tapir.bidding_round.models import BiddingRoundProduct, BiddingRoundProductPrice
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import PickupLocation, Product
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_now


class BidValidator:
    ALLOWED_QUANTITIES = [1, 2, 3, 4, 5]

    @classmethod
    def validate(
        cls, bidding_round, items: list[dict], pickup_location_id, cache, member=None
    ):
        cls._validate_round_is_open(bidding_round, cache=cache)
        if not items:
            raise ValidationError(_("Bitte mindestens einen Ernteanteil auswählen."))
        for item in items:
            cls._validate_item(bidding_round, item, cache=cache)
        cls._validate_pickup_locations(bidding_round, pickup_location_id, cache=cache)
        cls._validate_capacity(
            bidding_round, items, pickup_location_id, member, cache=cache
        )

    @classmethod
    def validate_admin_edit(
        cls, bidding_round, items: list[dict], pickup_location_id, cache, member=None
    ):
        if not items:
            raise ValidationError(_("Bitte mindestens einen Ernteanteil auswählen."))
        for item in items:
            cls._validate_item(bidding_round, item, cache=cache)
        cls._validate_pickup_locations(bidding_round, pickup_location_id, cache=cache)
        cls._validate_capacity(
            bidding_round, items, pickup_location_id, member, cache=cache
        )

    @classmethod
    def _validate_capacity(
        cls, bidding_round, items, pickup_location_id, member, cache
    ):
        from tapir.bidding_round.services.bidding_round_capacity_service import (
            BiddingRoundCapacityService,
        )

        reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
            bidding_round=bidding_round,
            items=items,
            pickup_location_id=pickup_location_id,
            member=member,
            cache=cache,
        )
        if not reasons:
            return
        raise ValidationError(
            BiddingRoundCapacityService.build_insufficient_capacity_message(reasons)
        )

    @classmethod
    def _validate_round_is_open(cls, bidding_round, cache):
        if bidding_round.status != ACTIVE:
            raise ValidationError(_("Die Beitragsrunde ist nicht aktiv."))
        now = get_now(cache=cache)
        if bidding_round.start_at and now < bidding_round.start_at:
            raise ValidationError(_("Die Beitragsrunde hat noch nicht begonnen."))
        if bidding_round.end_at and now > bidding_round.end_at:
            raise ValidationError(_("Die Beitragsrunde ist bereits beendet."))

    @classmethod
    def _validate_item(cls, bidding_round, item, cache):
        amounts = cls._parse_amounts(item)
        for amount in amounts.values():
            if amount is not None and amount < 0:
                raise ValidationError(_("Der Betrag darf nicht negativ sein."))

        cls._validate_levels(bidding_round, amounts)

        round_product = BiddingRoundProduct.objects.filter(
            id=item.get("round_product_id")
        ).first()
        if round_product is None or round_product.round_id != bidding_round.id:
            raise ValidationError(
                _("Der Ernteanteil gehört nicht zu dieser Beitragsrunde.")
            )
        product = Product.objects.filter(id=item.get("product_id")).first()
        if product is None or product.type_id != round_product.product_type_id:
            raise ValidationError(
                _("Das Produkt gehört nicht zum wählbaren Ernteanteil.")
            )
        min_amount = cls._get_min_amount(round_product, product)
        if min_amount is not None:
            for amount in amounts.values():
                if amount is not None and amount < min_amount:
                    raise ValidationError(
                        _("Der Betrag darf nicht unter dem Mindestpreis liegen.")
                    )
        quantity = item.get("quantity")
        if quantity not in cls.ALLOWED_QUANTITIES:
            raise ValidationError(_("Die Anzahl der Anteile ist ungültig."))
        if not cls._is_quantity_enabled(cache) and quantity != 1:
            raise ValidationError(_("Es kann nur ein Anteil angegeben werden."))

    @classmethod
    def _parse_amounts(cls, item) -> dict:
        amounts = {}
        for level in (1, 2, 3):
            raw = item.get(f"amount_{level}")
            if isinstance(raw, str):
                raw = raw.strip().replace("€", "").replace(",", ".")
            if raw in (None, ""):
                amounts[level] = None
                continue
            try:
                value = Decimal(raw)
            except (InvalidOperation, ValueError, TypeError):
                raise ValidationError(_("Bitte gib eine gültige Zahl ein."))
            if not value.is_finite():
                raise ValidationError(_("Bitte gib eine gültige Zahl ein."))
            amounts[level] = value
        return amounts

    @classmethod
    def _validate_levels(cls, bidding_round, amounts: dict):
        if bidding_round.bidding_procedure == TRAFFIC_LIGHT:
            if amounts[2] is None:
                raise ValidationError(_("Bitte den Gelb-Betrag (Zufrieden) angeben."))
        else:
            required_levels = bidding_round.bid_levels
            for level in range(1, required_levels + 1):
                if amounts[level] is None:
                    raise ValidationError(_("Bitte alle Gebote angeben."))
            for level in range(required_levels + 1, 4):
                if amounts[level] is not None:
                    raise ValidationError(_("Es wurden zu viele Gebote angegeben."))

        provided = [amounts[level] for level in (1, 2, 3) if amounts[level] is not None]
        for first, second in zip(provided, provided[1:]):
            if first > second:
                raise ValidationError(_("Die Gebote müssen aufsteigend sein."))

    @classmethod
    def _get_min_amount(cls, round_product, product):
        price = BiddingRoundProductPrice.objects.filter(
            round_product=round_product, product=product
        ).first()
        if price is None or price.min_amount is None:
            return None
        return price.min_amount

    @classmethod
    def _is_quantity_enabled(cls, cache) -> bool:
        try:
            return get_parameter_value(
                ParameterKeys.BIDDING_ROUND_BID_QUANTITY_ENABLED, cache=cache
            )
        except KeyError:
            return False

    @classmethod
    def _validate_pickup_locations(cls, bidding_round, pickup_location_id, cache):
        try:
            pickup_location_change_enabled = get_parameter_value(
                ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED, cache=cache
            )
        except KeyError:
            pickup_location_change_enabled = False
        if not pickup_location_change_enabled:
            return
        if not pickup_location_id:
            raise ValidationError(_("Bitte einen Abholort auswählen."))
        if not PickupLocation.objects.filter(id=pickup_location_id).exists():
            raise ValidationError(_("Der ausgewählte Abholort existiert nicht."))
