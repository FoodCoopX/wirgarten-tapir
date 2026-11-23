from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.bidding_round.models import BiddingRound, BiddingRoundProductPrice
from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.wirgarten.models import Member, Product, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys


class BiddingRoundViewService:
    @classmethod
    def is_feature_flag_enabled(cls, cache: dict) -> bool:
        return get_parameter_value(ParameterKeys.BIDDING_ROUND_ENABLED, cache=cache)

    @classmethod
    def is_public_url_enabled(cls, cache: dict) -> bool:
        return get_parameter_value(ParameterKeys.BIDDING_ROUND_URL_ENABLED, cache=cache)

    @classmethod
    def serialize_round(cls, bidding_round: BiddingRound, cache: dict) -> dict:
        return {
            "id": bidding_round.id,
            "name": bidding_round.name,
            "status": bidding_round.status,
            "start_at": bidding_round.start_at.isoformat(),
            "end_at": bidding_round.end_at.isoformat(),
            "contracts_created_at": (
                bidding_round.contracts_created_at.isoformat()
                if bidding_round.contracts_created_at
                else None
            ),
            "growing_period_id": bidding_round.growing_period_id,
            "comment": bidding_round.comment,
            "has_bids": (
                bidding_round.has_bids
                if hasattr(bidding_round, "has_bids")
                else bidding_round.bids.exists()
            ),
            "product": cls._serialize_round_product(bidding_round),
        }

    @classmethod
    def _serialize_round_product(cls, bidding_round: BiddingRound) -> dict:
        return {
            "product_type_id": bidding_round.product_type_id,
            "product_type_name": bidding_round.product_type.name,
            "target_amount_per_year": (
                str(bidding_round.target_amount_per_year)
                if bidding_round.target_amount_per_year is not None
                else None
            ),
            "prices": [
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    **cls._serialize_price_values(price),
                }
                for product, price in cls._get_products_with_prices(bidding_round)
            ],
        }

    @classmethod
    def _get_products_with_prices(
        cls, bidding_round: BiddingRound
    ) -> list[tuple[Product, BiddingRoundProductPrice | None]]:
        prices_by_product_id = {
            price.product_id: price
            for price in BiddingRoundProductPrice.objects.filter(round=bidding_round)
        }
        return [
            (product, prices_by_product_id.get(product.id))
            for product in Product.objects.filter(
                type_id=bidding_round.product_type_id, deleted=False
            )
        ]

    @classmethod
    def _serialize_price_values(cls, price: BiddingRoundProductPrice | None) -> dict:
        return {
            "reference_value": (
                str(price.reference_value)
                if price is not None and price.reference_value is not None
                else None
            ),
            "min_amount": (
                str(price.min_amount)
                if price is not None and price.min_amount is not None
                else None
            ),
            "size": (
                str(price.size)
                if price is not None and price.size is not None
                else None
            ),
        }

    @classmethod
    def serialize_bid(cls, bid, cache: dict) -> dict | None:
        if bid is None:
            return None
        pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                member_id=bid.member_id,
                reference_date=bid.round.growing_period.start_date,
                cache=cache,
            )
        )
        amount_per_year = (bid.amount_1 or Decimal("0")) * bid.quantity * 12
        return {
            "id": bid.id,
            "member_id": bid.member_id,
            "pickup_location_id": pickup_location_id,
            "updated_at": bid.updated_at.isoformat() if bid.updated_at else None,
            "product_id": bid.product_id,
            "product_name": bid.product.name,
            "quantity": bid.quantity,
            "amount_1": str(bid.amount_1) if bid.amount_1 is not None else None,
            "amount_per_year": str(amount_per_year),
            "total_per_year": str(amount_per_year),
        }

    @classmethod
    def build_texts(cls, cache: dict) -> dict:
        public_string_id_to_parameter_key_map = {
            "intro_title": ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TITLE,
            "intro_text": ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TEXT,
            "ended_text": ParameterKeys.BIDDING_ROUND_PUBLIC_ENDED_TEXT,
            "login_title": ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TITLE,
            "login_text": ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TEXT,
            "summary_title": ParameterKeys.BIDDING_ROUND_PUBLIC_SUMMARY_TITLE,
            "submit_label": ParameterKeys.BIDDING_ROUND_PUBLIC_SUBMIT_LABEL,
        }
        bid_string_id_to_parameter_key_map = {
            "amount_label": ParameterKeys.BIDDING_ROUND_BID_AMOUNT_LABEL,
            "reference_value_hint": ParameterKeys.BIDDING_ROUND_BID_REFERENCE_VALUE_HINT,
            "simple_explanation": ParameterKeys.BIDDING_ROUND_BID_SIMPLE_EXPLANATION,
            "live_yearly_label": ParameterKeys.BIDDING_ROUND_BID_LIVE_YEARLY_LABEL,
            "monthly_hint": ParameterKeys.BIDDING_ROUND_BID_MONTHLY_HINT,
            "monthly_unit": ParameterKeys.BIDDING_ROUND_BID_MONTHLY_UNIT,
            "yearly_unit": ParameterKeys.BIDDING_ROUND_BID_YEARLY_UNIT,
            "confirm_text": ParameterKeys.BIDDING_ROUND_BID_CONFIRM_TEXT,
            "success_text": ParameterKeys.BIDDING_ROUND_BID_SUCCESS_TEXT,
            "error_text": ParameterKeys.BIDDING_ROUND_BID_ERROR_TEXT,
        }

        return {
            **{
                string_id: get_parameter_value(parameter_key, cache=cache)
                for string_id, parameter_key in (
                    public_string_id_to_parameter_key_map.items()
                )
            },
            "bid": {
                string_id: get_parameter_value(parameter_key, cache=cache)
                for string_id, parameter_key in (
                    bid_string_id_to_parameter_key_map.items()
                )
            },
        }

    @classmethod
    def build_biddable_product(
        cls, bidding_round: BiddingRound, cache: dict, member: Member | None = None
    ) -> dict:
        products_with_prices = cls._get_products_with_prices(bidding_round)
        current_quantities = cls._get_current_quantities(
            member, [product for product, _price in products_with_prices]
        )
        return {
            "id": bidding_round.product_type_id,
            "product_type_id": bidding_round.product_type_id,
            "product_type_name": bidding_round.product_type.name,
            "products": [
                {
                    "id": product.id,
                    "name": product.name,
                    **cls._serialize_price_values(price),
                    "current_quantity": current_quantities.get(product.id),
                }
                for product, price in products_with_prices
            ],
        }

    @classmethod
    def _get_current_quantities(
        cls, member: Member | None, products: list[Product]
    ) -> dict:
        if member is None:
            return {}
        subscriptions = Subscription.objects.filter(
            member=member,
            product__in=products,
            cancellation_ts__isnull=True,
        ).order_by("product_id", "-period__start_date")
        quantities = {}
        for subscription in subscriptions.only("product_id", "quantity"):
            quantities.setdefault(subscription.product_id, subscription.quantity)
        return quantities

    @classmethod
    def serialize_validation_error(cls, error: ValidationError) -> str:
        return "; ".join(error.messages)
