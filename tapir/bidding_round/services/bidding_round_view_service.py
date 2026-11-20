from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext

from tapir.associations.services.association_membership_price_type_getter import (
    AssociationMembershipTypePriceGetter,
)
from tapir.bidding_round.config import BIDDING_ROUND_PROCEDURE_BID_RANGE
from tapir.bidding_round.models import BiddingRoundProductPrice
from tapir.bidding_round.services.bidding_round_delivery_charge_service import (
    BiddingRoundDeliveryChargeService,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Product, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys


class BiddingRoundViewService:
    @classmethod
    def _get_boolean_parameter(cls, key, default: bool, cache) -> bool:
        try:
            return get_parameter_value(key, cache=cache)
        except KeyError:
            return default

    @classmethod
    def is_feature_flag_enabled(cls, cache) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_ENABLED, False, cache
        )

    @classmethod
    def is_public_url_enabled(cls, cache) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_URL_ENABLED, True, cache
        )

    @classmethod
    def public_access_allowed(cls, user, cache) -> bool:
        """Whether the public bidding-round pages may serve this user.

        Anonymous visitors only get access while the public URL switch is on;
        authenticated members always do. The master switch is checked separately
        because it hides the pages entirely.
        """
        return cls.is_public_url_enabled(cache) or (
            user is not None and user.is_authenticated
        )

    @classmethod
    def is_status_enabled(cls, cache) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_STATUS_ENABLED, True, cache
        )

    @classmethod
    def is_status_public_enabled(cls, cache) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_STATUS_PUBLIC_ENABLED, True, cache
        )

    @classmethod
    def is_bid_shares_enabled(cls, cache) -> bool:
        """Presentation switch: hides the share quantity controls in the wizard.

        Purely a UI flag; bids are validated independently, so toggling it does not
        invalidate existing bids.
        """
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_BID_SHARES_ENABLED, False, cache
        )

    @classmethod
    def is_bid_carousel_enabled(cls, cache) -> bool:
        """Presentation switch: hides the product carousel in the wizard.

        Purely a UI flag; bids are validated independently, so toggling it does not
        invalidate existing bids.
        """
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_BID_CAROUSEL_ENABLED, False, cache
        )

    @classmethod
    def is_sepa_enabled(cls, cache) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_SEPA_ENABLED, True, cache
        )

    @classmethod
    def is_feedback_enabled(cls, cache) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_FEEDBACK_ENABLED, True, cache
        )

    @classmethod
    def is_auto_renewal_enabled(cls, cache) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, False, cache
        )

    @classmethod
    def build_member_data(cls, member, bidding_round, cache) -> dict:
        if member is None:
            return {}
        reference_date = bidding_round.growing_period.start_date
        association_membership = TapirCache.get_member_association_membership_at_date(
            cache=cache, member=member, reference_date=reference_date
        )
        return {
            "account_owner": member.account_owner,
            "iban": member.iban,
            "payment_rhythm": MemberPaymentRhythmService.get_member_payment_rhythm(
                member=member,
                reference_date=reference_date,
                cache=cache,
            ),
            "association_membership": (
                {
                    "name": association_membership.type.name,
                    "price": str(
                        AssociationMembershipTypePriceGetter.get_price(
                            membership_type=association_membership.type,
                            reference_date=reference_date,
                            cache=cache,
                        )
                    ),
                }
                if association_membership is not None
                else None
            ),
        }

    @classmethod
    def get_display_name(cls, cache) -> str:
        return gettext("Beitragsrunde")

    @classmethod
    def serialize_round(
        cls, bidding_round, cache, display_name: str | None = None
    ) -> dict:
        if display_name is None:
            display_name = cls.get_display_name(cache)
        return {
            "id": bidding_round.id,
            "name": bidding_round.name,
            "display_name": display_name,
            "status": bidding_round.status,
            "bidding_procedure": bidding_round.bidding_procedure,
            "bid_levels": bidding_round.bid_levels,
            "include_auto_renewed": bidding_round.include_auto_renewed,
            "average_bid_locked_at": (
                bidding_round.average_bid_locked_at.isoformat()
                if bidding_round.average_bid_locked_at
                else None
            ),
            "locked_bid_range_position": (
                str(bidding_round.locked_bid_range_position)
                if bidding_round.locked_bid_range_position is not None
                else None
            ),
            "locked_bidder_average_per_share_per_month": (
                str(bidding_round.locked_bidder_average_per_share_per_month)
                if bidding_round.locked_bidder_average_per_share_per_month is not None
                else None
            ),
            "locked_surcharge_percent": str(bidding_round.locked_surcharge_percent),
            "locked_surcharge_on_bids": bidding_round.locked_surcharge_on_bids,
            "locked_surcharge_on_average": bidding_round.locked_surcharge_on_average,
            "start_at": (
                bidding_round.start_at.isoformat() if bidding_round.start_at else None
            ),
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
    def _get_round_product_type(cls, bidding_round):
        return bidding_round.product_types.select_related("product_type").first()

    @classmethod
    def _serialize_round_product(cls, bidding_round) -> dict | None:
        round_product_type = cls._get_round_product_type(bidding_round)
        if round_product_type is None:
            return None
        return {
            "product_type_id": round_product_type.product_type_id,
            "product_type_name": round_product_type.product_type.name,
            "target_amount_per_year": (
                str(round_product_type.target_amount_per_year)
                if round_product_type.target_amount_per_year is not None
                else None
            ),
            "prices": [
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    **cls._serialize_price_values(price),
                }
                for product, price in cls._get_products_with_prices(round_product_type)
            ],
        }

    @classmethod
    def _get_round_product_type(cls, bidding_round):
        return bidding_round.product_types.select_related("product_type").first()

    @classmethod
    def _get_products_with_prices(cls, round_product_type) -> list[tuple]:
        prices_by_product_id = {
            price.product_id: price
            for price in BiddingRoundProductPrice.objects.filter(
                round_product_type=round_product_type
            )
        }
        return [
            (product, prices_by_product_id.get(product.id))
            for product in Product.objects.filter(
                type_id=round_product_type.product_type_id, deleted=False
            )
        ]

    @classmethod
    def _serialize_price_values(cls, price) -> dict:
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
    def serialize_bid_item(cls, bid_item) -> dict:
        counting_amount = cls._counting_amount(bid_item)
        return {
            "round_product_type_id": bid_item.round_product_type_id,
            "product_type_name": bid_item.round_product_type.product_type.name,
            "product_id": bid_item.product_id,
            "product_name": bid_item.product.name,
            "quantity": bid_item.quantity,
            "amount_1": (
                str(bid_item.amount_1) if bid_item.amount_1 is not None else None
            ),
            "amount_2": (
                str(bid_item.amount_2) if bid_item.amount_2 is not None else None
            ),
            "amount_3": (
                str(bid_item.amount_3) if bid_item.amount_3 is not None else None
            ),
            "amount_per_year": str(counting_amount * bid_item.quantity * 12),
        }

    @staticmethod
    def _counting_amount(bid_item, bidding_round=None) -> Decimal:
        if bidding_round is None:
            bidding_round = bid_item.bid.round
        if bidding_round.bidding_procedure == BIDDING_ROUND_PROCEDURE_BID_RANGE:
            green = bid_item.amount_1 or bid_item.amount_2 or Decimal("0")
            red = bid_item.amount_2 or bid_item.amount_1 or Decimal("0")
            return (green + red) / Decimal("2")
        return (
            bid_item.amount_2 or bid_item.amount_1 or bid_item.amount_3 or Decimal("0")
        )

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
        items = list(
            bid.items.select_related(
                "round_product_type__product_type", "product"
            ).all()
        )
        return {
            "id": bid.id,
            "member_id": bid.member_id,
            "entered_by_admin": bid.entered_by_admin,
            "admin_confirmed": (
                bid.admin_confirmed.isoformat() if bid.admin_confirmed else None
            ),
            "pickup_location_id": pickup_location_id,
            "updated_at": bid.updated_at.isoformat() if bid.updated_at else None,
            "total_per_year": str(
                sum(
                    (cls._counting_amount(item) * item.quantity * 12 for item in items),
                    Decimal("0"),
                )
            ),
            "items": [cls.serialize_bid_item(item) for item in items],
        }

    @classmethod
    def build_texts(cls, cache) -> dict:
        public_string_id_to_parameter_key_map = {
            "intro_title": ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TITLE,
            "intro_text": ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TEXT,
            "ended_text": ParameterKeys.BIDDING_ROUND_PUBLIC_ENDED_TEXT,
            "login_title": ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TITLE,
            "login_text": ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TEXT,
            "summary_title": ParameterKeys.BIDDING_ROUND_PUBLIC_SUMMARY_TITLE,
            "privacy_title": ParameterKeys.BIDDING_ROUND_PUBLIC_PRIVACY_TITLE,
            "pickup_location_title": (
                ParameterKeys.BIDDING_ROUND_PUBLIC_PICKUP_LOCATION_TITLE
            ),
            "submit_label": ParameterKeys.BIDDING_ROUND_PUBLIC_SUBMIT_LABEL,
            "final_submit_label": (
                ParameterKeys.BIDDING_ROUND_PUBLIC_FINAL_SUBMIT_LABEL
            ),
        }
        bid_string_id_to_parameter_key_map = {
            "amount_label": ParameterKeys.BIDDING_ROUND_BID_AMOUNT_LABEL,
            "reference_value_hint": ParameterKeys.BIDDING_ROUND_BID_REFERENCE_VALUE_HINT,
            "simple_explanation": ParameterKeys.BIDDING_ROUND_BID_SIMPLE_EXPLANATION,
            "bid_range_explanation": (
                ParameterKeys.BIDDING_ROUND_BID_RANGE_EXPLANATION
            ),
            "level_1_label": ParameterKeys.BIDDING_ROUND_BID_LEVEL_1_LABEL,
            "level_2_label": ParameterKeys.BIDDING_ROUND_BID_LEVEL_2_LABEL,
            "level_3_label": ParameterKeys.BIDDING_ROUND_BID_LEVEL_3_LABEL,
            "green_label": ParameterKeys.BIDDING_ROUND_BID_GREEN_LABEL,
            "yellow_label": ParameterKeys.BIDDING_ROUND_BID_YELLOW_LABEL,
            "red_label": ParameterKeys.BIDDING_ROUND_BID_RED_LABEL,
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
    def build_biddable_product(cls, bidding_round, cache, member=None) -> dict | None:
        round_product_type = cls._get_round_product_type(bidding_round)
        if round_product_type is None:
            return None

        products_with_prices = cls._get_products_with_prices(round_product_type)
        current_quantities = cls._get_current_quantities(
            member, [product for product, _price in products_with_prices]
        )
        return {
            "id": round_product_type.id,
            "product_type_id": round_product_type.product_type_id,
            "product_type_name": round_product_type.product_type.name,
            "products": [
                {
                    "id": product.id,
                    "name": product.name,
                    **cls._serialize_price_values(price),
                    "current_quantity": current_quantities.get(product.id),
                    "image_url": product.url_of_image_in_bestellwizard or None,
                }
                for product, price in products_with_prices
            ],
        }

    @classmethod
    def _get_current_quantities(cls, member, products) -> dict:
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
    def build_current_pickup_location(cls, bidding_round, member, cache):
        pickup_location = MemberPickupLocationGetter.get_member_pickup_location(
            member=member,
            reference_date=bidding_round.growing_period.start_date,
            cache=cache,
        )
        if pickup_location is None:
            return None
        round_product_type = cls._get_round_product_type(bidding_round)
        product_type = (
            round_product_type.product_type if round_product_type is not None else None
        )
        yearly_delivery_charge = (
            BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
                pickup_location_id=pickup_location.id,
                product_type=product_type,
                growing_period=bidding_round.growing_period,
                cache=cache,
            )
        )
        return {
            "id": pickup_location.id,
            "name": pickup_location.name,
            "yearly_delivery_charge": str(yearly_delivery_charge),
        }

    @classmethod
    def build_bid_options(cls, cache) -> dict:
        return {
            "quantity_enabled": cls.is_bid_shares_enabled(cache),
            "carousel_enabled": cls.is_bid_carousel_enabled(cache),
        }

    @classmethod
    def serialize_validation_error(cls, error: ValidationError) -> str:
        return "; ".join(error.messages)
