from django.core.exceptions import ValidationError
from django.utils.translation import gettext

from tapir.associations.services.association_membership_price_type_getter import (
    AssociationMembershipTypePriceGetter,
)
from tapir.bidding_round.config import BIDDING_ROUND_PROCEDURE_BID_RANGE
from tapir.bidding_round.models import BiddingRound, BiddingRoundProductPrice
from tapir.bidding_round.serializers import (
    BiddableProductSerializer,
    BidSerializer,
    RoundSerializer,
    RoundTextsSerializer,
)
from tapir.bidding_round.services.bidding_round_delivery_charge_service import (
    BiddingRoundDeliveryChargeService,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.serializers import PublicPickupLocationSerializer
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, PickupLocation, Product, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_product_price


class BiddingRoundViewService:
    @classmethod
    def _get_boolean_parameter(cls, key, default: bool, cache) -> bool:
        try:
            return get_parameter_value(key, cache=cache)
        except KeyError:
            return default

    @classmethod
    def is_feature_flag_enabled(cls, cache: dict) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_ENABLED, False, cache
        )

    @classmethod
    def is_public_url_enabled(cls, cache: dict) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_URL_ENABLED, True, cache
        )

    @classmethod
    def public_access_allowed(cls, user, cache: dict) -> bool:
        """Whether the public bidding-round pages may serve this user.

        Anonymous visitors only get access while the public URL switch is on;
        authenticated members always do. The master switch is checked separately
        because it hides the pages entirely.
        """
        return cls.is_public_url_enabled(cache) or (
            user is not None and user.is_authenticated
        )

    @classmethod
    def is_status_enabled(cls, cache: dict) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_STATUS_ENABLED, True, cache
        )

    @classmethod
    def is_status_public_enabled(cls, cache: dict) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_STATUS_PUBLIC_ENABLED, True, cache
        )

    @classmethod
    def is_bid_shares_enabled(cls, cache: dict) -> bool:
        """Presentation switch: hides the share quantity controls in the wizard.

        Purely a UI flag; bids are validated independently, so toggling it does not
        invalidate existing bids.
        """
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_BID_SHARES_ENABLED, False, cache
        )

    @classmethod
    def is_bid_carousel_enabled(cls, cache: dict) -> bool:
        """Presentation switch: hides the product carousel in the wizard.

        Purely a UI flag; bids are validated independently, so toggling it does not
        invalidate existing bids.
        """
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_BID_CAROUSEL_ENABLED, False, cache
        )

    @classmethod
    def is_sepa_enabled(cls, cache: dict) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_SEPA_ENABLED, True, cache
        )

    @classmethod
    def is_feedback_enabled(cls, cache: dict) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.BIDDING_ROUND_FEEDBACK_ENABLED, True, cache
        )

    @classmethod
    def is_auto_renewal_enabled(cls, cache: dict) -> bool:
        return cls._get_boolean_parameter(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, False, cache
        )

    @classmethod
    def get_display_name(cls, cache: dict) -> str:
        return gettext("Beitragsrunde")

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
    def serialize_round(
        cls, bidding_round: BiddingRound, cache: dict, display_name=None
    ) -> dict:
        if display_name is None:
            display_name = cls.get_display_name(cache)
        return RoundSerializer(
            bidding_round,
            context={"cache": cache, "display_name": display_name},
        ).data

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
    def get_effective_amount(
        cls, bid, effective_position=None, bidding_round=None
    ) -> Decimal:
        if effective_position is None:
            return cls._counting_amount(bid, bidding_round)
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        return BiddingRoundStatsService.get_effective_amount(
            bid, effective_position, bidding_round
        )

    @classmethod
    def serialize_bid(
        cls, bid, effective_position=None, bid_range_position=None, *, cache: dict
    ) -> dict | None:
        if bid is None:
            return None
        if effective_position is None:
            effective_position = bid_range_position
        return BidSerializer(
            bid, context={"cache": cache, "position": effective_position}
        ).data

    @classmethod
    def build_texts(cls, cache: dict) -> dict:
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

        texts = {
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
        return RoundTextsSerializer(texts).data

    @classmethod
    def build_biddable_product(
        cls, bidding_round: BiddingRound, cache: dict, member: Member | None = None
    ) -> dict:
        products_with_prices = [
            (product, price)
            for product, price in cls._get_products_with_prices(bidding_round)
            if price is not None
        ]
        current_quantities = cls._get_current_quantities(
            member, [product for product, _price in products_with_prices]
        )
        capacity = TapirCache.get_product_type_capacity_at_date(
            cache=cache,
            product_type=bidding_round.product_type,
            reference_date=bidding_round.growing_period.start_date,
        )
        data = {
            "id": bidding_round.product_type_id,
            "product_type_id": bidding_round.product_type_id,
            "product_type_name": bidding_round.product_type.name,
            "capacity_id": capacity.id if capacity is not None else None,
            "products": [
                {
                    "id": product.id,
                    "name": product.name,
                    **cls._serialize_price_values(price),
                    "standard_price": cls._get_standard_price(
                        product, bidding_round, cache
                    ),
                    "current_quantity": current_quantities.get(product.id),
                    "image_url": product.url_of_image_in_bestellwizard or None,
                }
                for product, price in products_with_prices
            ],
        }
        return BiddableProductSerializer(data).data

    @classmethod
    def _get_standard_price(cls, product, bidding_round, cache) -> str | None:
        product_price = get_product_price(
            product,
            reference_date=bidding_round.growing_period.start_date,
            cache=cache,
        )
        return str(product_price.price) if product_price is not None else None

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
    def build_current_pickup_location(cls, bidding_round, member, cache):
        pickup_location = MemberPickupLocationGetter.get_member_pickup_location(
            member=member,
            reference_date=bidding_round.growing_period.start_date,
            cache=cache,
        )
        if pickup_location is None:
            return None
        yearly_delivery_charge = (
            BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
                pickup_location_id=pickup_location.id,
                product_type=bidding_round.product_type,
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
    def build_pickup_locations(cls, bidding_round, cache) -> list:
        from tapir.bidding_round.services.bidding_round_stats_service import (
            BiddingRoundStatsService,
        )

        growing_period = bidding_round.growing_period
        utilization = BiddingRoundStatsService.build_public_pickup_location_utilization(
            bidding_round, cache=cache
        )

        locations = list(PickupLocation.objects.prefetch_related("opening_times").all())
        serializer_context = {
            "cache": cache,
            "reference_date_for_delivery_charge": growing_period.start_date,
        }
        serialized_locations = list(
            PublicPickupLocationSerializer(
                locations, many=True, context=serializer_context
            ).data
        )

        result = []
        for location, serialized_location in zip(locations, serialized_locations):
            entry = dict(serialized_location)
            entry["yearly_delivery_charge"] = str(
                BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
                    pickup_location_id=location.id,
                    product_type=bidding_round.product_type,
                    growing_period=growing_period,
                    cache=cache,
                )
            )
            entry["utilization"] = utilization.get(location.id)
            result.append(entry)
        return result

    @classmethod
    def parse_bool(cls, value):
        if value is None:
            return None
        return value.lower() in ("true", "1", "yes")

    @classmethod
    def filter_and_sort_members(cls, members, filter_, sort):
        if filter_ == "active_in_contract_period":
            members = [
                member
                for member in members
                if member.get("is_active_in_contract_period", True)
            ]
        elif filter_ == "has_bid":
            members = [member for member in members if member["has_bid"]]
        elif filter_ == "no_bid":
            members = [
                member
                for member in members
                if not member["has_bid"]
                and member.get("is_active_in_contract_period", True)
            ]
        elif filter_ == "auto_renewed":
            members = [member for member in members if member["is_auto_renewed"]]
        if sort == "date":
            return sorted(
                members,
                key=lambda member: (member["bid"] or {}).get("updated_at") or "",
                reverse=True,
            )
        return sorted(members, key=lambda member: member["member_name"].lower())

    @classmethod
    def serialize_validation_error(cls, error: ValidationError) -> str:
        return "; ".join(error.messages)
