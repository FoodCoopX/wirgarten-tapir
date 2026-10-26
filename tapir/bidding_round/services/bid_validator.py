from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import ACTIVE, TRAFFIC_LIGHT
from tapir.bidding_round.models import BiddingRoundProduct, BiddingRoundProductPrice
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import Product
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
            raise ValidationError(_("Please select at least one harvest share."))
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
            raise ValidationError(_("Please select at least one harvest share."))
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
            raise ValidationError(_("The bidding round is not active."))
        now = get_now(cache=cache)
        if bidding_round.start_at and now < bidding_round.start_at:
            raise ValidationError(_("The bidding round has not started yet."))
        if bidding_round.end_at and now > bidding_round.end_at:
            raise ValidationError(_("The bidding round has already ended."))

    @classmethod
    def _validate_item(cls, bidding_round, item, cache):
        amounts = cls._parse_amounts(item)
        for amount in amounts.values():
            if amount is not None and amount < 0:
                raise ValidationError(_("The amount must not be negative."))

        cls._validate_levels(bidding_round, amounts)

        round_product = BiddingRoundProduct.objects.get(id=item["round_product_id"])
        product = Product.objects.get(id=item["product_id"])
        if product.type_id != round_product.product_type_id:
            raise ValidationError(
                _("The product does not belong to the biddable harvest share.")
            )
        min_amount = cls._get_min_amount(round_product, product)
        if min_amount is not None:
            for amount in amounts.values():
                if amount is not None and amount < min_amount:
                    raise ValidationError(
                        _("The amount must not be below the minimum price.")
                    )
        if item["quantity"] not in cls.ALLOWED_QUANTITIES:
            raise ValidationError(_("The number of shares is invalid."))

    @classmethod
    def _parse_amounts(cls, item) -> dict:
        amounts = {}
        for level in (1, 2, 3):
            raw = item.get(f"amount_{level}")
            if isinstance(raw, str):
                raw = raw.strip().replace("€", "").replace(",", ".")
            amounts[level] = None if raw in (None, "") else Decimal(raw)
        return amounts

    @classmethod
    def _validate_levels(cls, bidding_round, amounts: dict):
        if bidding_round.bidding_procedure == TRAFFIC_LIGHT:
            if amounts[2] is None:
                raise ValidationError(
                    _("Please provide the yellow amount (satisfied).")
                )
        else:
            required_levels = bidding_round.bid_levels
            for level in range(1, required_levels + 1):
                if amounts[level] is None:
                    raise ValidationError(_("Please provide all bids."))
            for level in range(required_levels + 1, 4):
                if amounts[level] is not None:
                    raise ValidationError(_("Too many bids were provided."))

        provided = [amounts[level] for level in (1, 2, 3) if amounts[level] is not None]
        for first, second in zip(provided, provided[1:]):
            if first > second:
                raise ValidationError(_("The bids must be in ascending order."))

    @classmethod
    def _get_min_amount(cls, round_product, product):
        price = BiddingRoundProductPrice.objects.filter(
            round_product=round_product, product=product
        ).first()
        if price is None or price.min_amount is None:
            return None
        return price.min_amount

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
            raise ValidationError(_("Please select a pickup location."))
