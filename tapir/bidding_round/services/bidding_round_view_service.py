from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext

from tapir.bidding_round.models import BiddingRoundProductPrice
from tapir.bidding_round.services.bidding_round_delivery_charge_service import (
    BiddingRoundDeliveryChargeService,
)
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.serializers import PublicPickupLocationSerializer
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    PickupLocation,
    Product,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_product_price


class BiddingRoundViewService:
    @classmethod
    def is_feature_flag_enabled(cls, cache) -> bool:
        try:
            return get_parameter_value(ParameterKeys.BIDDING_ROUND_ENABLED, cache=cache)
        except KeyError:
            return False

    @classmethod
    def is_public_url_enabled(cls, cache) -> bool:
        try:
            return get_parameter_value(
                ParameterKeys.BIDDING_ROUND_URL_ENABLED, cache=cache
            )
        except KeyError:
            return True

    @classmethod
    def get_display_name(cls, cache) -> str:
        return gettext("Bidding round")

    @classmethod
    def get_rounds_display_name(cls, cache) -> str:
        return gettext("Bidding rounds")

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
            "start_at": (
                bidding_round.start_at.isoformat() if bidding_round.start_at else None
            ),
            "end_at": bidding_round.end_at.isoformat(),
            "include_auto_renewed": bidding_round.include_auto_renewed,
            "contracts_created_at": bidding_round.contracts_created_at,
            "average_bid_locked_at": bidding_round.average_bid_locked_at,
            "locked_traffic_light_position": (
                str(bidding_round.locked_traffic_light_position)
                if bidding_round.locked_traffic_light_position is not None
                else None
            ),
            "locked_average_bid_per_share_per_month": (
                str(bidding_round.locked_average_bid_per_share_per_month)
                if bidding_round.locked_average_bid_per_share_per_month is not None
                else None
            ),
            "locked_average_bid_per_share_per_year": (
                str(bidding_round.locked_average_bid_per_share_per_year)
                if bidding_round.locked_average_bid_per_share_per_year is not None
                else None
            ),
            "locked_bidder_average_per_share_per_month": (
                str(bidding_round.locked_bidder_average_per_share_per_month)
                if bidding_round.locked_bidder_average_per_share_per_month is not None
                else None
            ),
            "locked_bidder_average_per_share_per_year": (
                str(bidding_round.locked_bidder_average_per_share_per_year)
                if bidding_round.locked_bidder_average_per_share_per_year is not None
                else None
            ),
            "locked_surcharge_percent": str(bidding_round.locked_surcharge_percent),
            "locked_surcharge_on_bids": bidding_round.locked_surcharge_on_bids,
            "locked_surcharge_on_average": bidding_round.locked_surcharge_on_average,
            "growing_period_id": bidding_round.growing_period_id,
            "comment": bidding_round.comment,
            "has_bids": getattr(bidding_round, "has_bids", bidding_round.bids.exists()),
            "product": cls._serialize_round_product(bidding_round),
        }

    @classmethod
    def _serialize_round_product(cls, bidding_round) -> dict | None:
        round_product = bidding_round.products.select_related("product_type").first()
        if round_product is None:
            return None
        return {
            "product_type_id": round_product.product_type_id,
            "product_type_name": round_product.product_type.name,
        }

    @classmethod
    def serialize_bid_item(
        cls, bid_item, bidding_round, effective_position, cache
    ) -> dict:
        effective_amount = BiddingRoundStatsService.get_effective_amount(
            bid_item, bidding_round, position=effective_position, cache=cache
        )
        return {
            "round_product_id": bid_item.round_product_id,
            "product_type_name": bid_item.round_product.product_type.name,
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
            "effective_amount": str(effective_amount),
            "amount_per_year": str(effective_amount * bid_item.quantity * 12),
        }

    @classmethod
    def serialize_bid(cls, bid, effective_position, cache) -> dict:
        if bid is None:
            return None
        items = list(
            bid.items.select_related("round_product__product_type", "product").all()
        )
        return {
            "id": bid.id,
            "member_id": bid.member_id,
            "pickup_location_id": bid.pickup_location_id,
            "pickup_location_name": (
                bid.pickup_location.name if bid.pickup_location_id else None
            ),
            "entered_by_admin": bid.entered_by_admin,
            "admin_confirmed": bid.admin_confirmed,
            "updated_at": bid.updated_at.isoformat() if bid.updated_at else None,
            "total_per_year": str(
                sum(
                    (
                        BiddingRoundStatsService.get_effective_amount(
                            item, bid.round, position=effective_position, cache=cache
                        )
                        * item.quantity
                        * 12
                        for item in items
                    ),
                    Decimal("0"),
                )
            ),
            "items": [
                cls.serialize_bid_item(item, bid.round, effective_position, cache)
                for item in items
            ],
        }

    @classmethod
    def serialize_contracts(cls, bidding_round, cache, position=None) -> list:
        """Rows of the contracts that exist for the round's season: contracts created by
        the round and already materialised auto-renewed contracts."""
        if position is None:
            position = BiddingRoundStatsService.get_default_position(
                bidding_round, cache=cache
            )
        rows = {}
        cls._add_bidder_contract_rows(rows, bidding_round, cache, position)
        cls._add_auto_renewed_contract_rows(rows, bidding_round, cache)
        ordered = sorted(
            rows.values(), key=lambda row: (row["member_name"] or "").lower()
        )
        return cls._finalize_contract_rows(ordered)

    @classmethod
    def _add_bidder_contract_rows(cls, rows, bidding_round, cache, position) -> None:
        reference_date = bidding_round.growing_period.start_date
        bids_by_member_id = {
            bid.member_id: bid
            for bid in bidding_round.bids.select_related("pickup_location")
            .prefetch_related("items")
            .all()
        }
        for link in (
            bidding_round.created_subscriptions.filter(is_bidder_contract=True)
            .select_related(
                "subscription__member",
                "subscription__product",
                "subscription__product__type",
            )
            .all()
        ):
            subscription = link.subscription
            bid = bids_by_member_id.get(subscription.member_id)
            row = rows.setdefault(
                subscription.member_id,
                cls._new_contract_row(
                    member=subscription.member,
                    type_="bid",
                    pickup_location_name=(
                        bid.pickup_location.name
                        if bid is not None and bid.pickup_location_id
                        else ""
                    ),
                    is_created=True,
                ),
            )
            row["items"].append(cls._build_contract_item(subscription))
            row["standard_amount_per_month"] += cls._get_product_monthly_price(
                subscription, reference_date, cache
            )
            row["amount_per_month"] += cls._get_bidder_monthly_amount(
                bidding_round, subscription, bids_by_member_id, position, cache
            )

    @classmethod
    def _add_auto_renewed_contract_rows(cls, rows, bidding_round, cache) -> None:
        reference_date = bidding_round.growing_period.start_date
        product_type_ids = set(
            bidding_round.products.values_list("product_type_id", flat=True)
        )
        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        linked_subscription_ids = set(
            bidding_round.created_subscriptions.values_list(
                "subscription_id", flat=True
            )
        )
        subscriptions = (
            Subscription.objects.filter(
                period=bidding_round.growing_period,
                cancellation_ts__isnull=True,
                product__type_id__in=product_type_ids,
            )
            .exclude(member_id__in=bid_member_ids)
            .select_related("member", "product", "product__type")
        )
        for subscription in subscriptions:
            reference_value = BiddingRoundStatsService.get_reference_value(
                bidding_round, subscription.product
            )
            product_price = get_product_price(
                subscription.product, reference_date, cache=cache
            )
            size = (
                Decimal(product_price.size)
                if product_price is not None and product_price.size
                else Decimal("1")
            )
            standard_amount_per_month = (
                product_price.price if product_price is not None else Decimal("0")
            ) * subscription.quantity
            is_created = subscription.id in linked_subscription_ids
            row = rows.setdefault(
                subscription.member_id,
                cls._new_contract_row(
                    member=subscription.member,
                    type_="auto_renewed",
                    pickup_location_name=cls._get_member_pickup_location_name(
                        subscription.member_id, reference_date, cache
                    ),
                    is_created=is_created,
                ),
            )
            row["is_created"] = row["is_created"] or is_created
            row["items"].append(cls._build_contract_item(subscription))
            row["standard_amount_per_month"] += standard_amount_per_month
            row["amount_per_month"] += reference_value * size * subscription.quantity

    @classmethod
    def _new_contract_row(cls, member, type_, pickup_location_name, is_created) -> dict:
        return {
            "member_id": member.id,
            "member_name": f"{member.first_name} {member.last_name}",
            "member_email": member.email,
            "type": type_,
            "items": [],
            "pickup_location_name": pickup_location_name,
            "standard_amount_per_month": Decimal("0"),
            "amount_per_month": Decimal("0"),
            "is_created": is_created,
        }

    @classmethod
    def _build_contract_item(cls, subscription) -> dict:
        return {
            "product_type_name": subscription.product.type.name,
            "product_name": subscription.product.name,
            "quantity": subscription.quantity,
        }

    @classmethod
    def _get_member_pickup_location_name(cls, member_id, reference_date, cache) -> str:
        pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                member_id=member_id, reference_date=reference_date, cache=cache
            )
        )
        if not pickup_location_id:
            return ""
        pickup_location = PickupLocation.objects.filter(id=pickup_location_id).first()
        return pickup_location.name if pickup_location else ""

    @classmethod
    def _get_product_monthly_price(cls, subscription, reference_date, cache) -> Decimal:
        product_price = get_product_price(
            subscription.product, reference_date, cache=cache
        )
        return (
            product_price.price if product_price is not None else Decimal("0")
        ) * subscription.quantity

    @classmethod
    def _get_bidder_monthly_amount(
        cls, bidding_round, subscription, bids_by_member_id, position, cache
    ) -> Decimal:
        bid = bids_by_member_id.get(subscription.member_id)
        if bid is not None:
            item = next(
                (
                    bid_item
                    for bid_item in bid.items.all()
                    if bid_item.product_id == subscription.product_id
                ),
                None,
            )
            if item is not None:
                return (
                    BiddingRoundStatsService.get_effective_amount(
                        item, bidding_round, position=position, cache=cache
                    )
                    * subscription.quantity
                )
        return cls._get_product_monthly_price(
            subscription, bidding_round.growing_period.start_date, cache
        )

    @classmethod
    def _finalize_contract_rows(cls, rows) -> list:
        for row in rows:
            row["contribution_amount_per_month"] = (
                row["amount_per_month"] - row["standard_amount_per_month"]
            )
            row["standard_amount_per_year"] = row["standard_amount_per_month"] * 12
            row["contribution_amount_per_year"] = (
                row["contribution_amount_per_month"] * 12
            )
            row["amount_per_year"] = row["amount_per_month"] * 12
        return rows

    @classmethod
    def build_texts(cls, cache) -> dict:
        public_string_id_to_parameter_key_map = {
            "intro_title": ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TITLE,
            "intro_text": ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TEXT,
            "ended_text": ParameterKeys.BIDDING_ROUND_PUBLIC_ENDED_TEXT,
            "login_title": ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TITLE,
            "login_text": ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TEXT,
            "stats_title": ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_TITLE,
            "stats_text": ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_TEXT,
            "stats_explanation": ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_EXPLANATION,
            "stats_traffic_light_slider_hint": (
                ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_TRAFFIC_LIGHT_SLIDER_HINT
            ),
            "stats_simple_levels_slider_hint": (
                ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_SIMPLE_LEVELS_SLIDER_HINT
            ),
            "pickup_location_title": (
                ParameterKeys.BIDDING_ROUND_PUBLIC_PICKUP_LOCATION_TITLE
            ),
            "pickup_location_text": (
                ParameterKeys.BIDDING_ROUND_PUBLIC_PICKUP_LOCATION_TEXT
            ),
            "summary_title": ParameterKeys.BIDDING_ROUND_PUBLIC_SUMMARY_TITLE,
            "submit_label": ParameterKeys.BIDDING_ROUND_PUBLIC_SUBMIT_LABEL,
        }
        bid_string_id_to_parameter_key_map = {
            "product_label": ParameterKeys.BIDDING_ROUND_BID_PRODUCT_LABEL,
            "variant_label": ParameterKeys.BIDDING_ROUND_BID_VARIANT_LABEL,
            "quantity_label": ParameterKeys.BIDDING_ROUND_BID_QUANTITY_LABEL,
            "amount_label": ParameterKeys.BIDDING_ROUND_BID_AMOUNT_LABEL,
            "reference_value_hint": ParameterKeys.BIDDING_ROUND_BID_REFERENCE_VALUE_HINT,
            "simple_explanation": ParameterKeys.BIDDING_ROUND_BID_SIMPLE_EXPLANATION,
            "traffic_light_explanation": ParameterKeys.BIDDING_ROUND_BID_TRAFFIC_LIGHT_EXPLANATION,
            "simple_levels_explanation": (
                ParameterKeys.BIDDING_ROUND_BID_SIMPLE_LEVELS_EXPLANATION
            ),
            "level_1_label": ParameterKeys.BIDDING_ROUND_BID_LEVEL_1_LABEL,
            "level_2_label": ParameterKeys.BIDDING_ROUND_BID_LEVEL_2_LABEL,
            "level_3_label": ParameterKeys.BIDDING_ROUND_BID_LEVEL_3_LABEL,
            "green_label": ParameterKeys.BIDDING_ROUND_BID_GREEN_LABEL,
            "yellow_label": ParameterKeys.BIDDING_ROUND_BID_YELLOW_LABEL,
            "red_label": ParameterKeys.BIDDING_ROUND_BID_RED_LABEL,
            "pickup_location_label": (
                ParameterKeys.BIDDING_ROUND_BID_PICKUP_LOCATION_LABEL
            ),
            "live_yearly_label": ParameterKeys.BIDDING_ROUND_BID_LIVE_YEARLY_LABEL,
            "monthly_hint": ParameterKeys.BIDDING_ROUND_BID_MONTHLY_HINT,
            "monthly_unit": ParameterKeys.BIDDING_ROUND_BID_MONTHLY_UNIT,
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
    def build_biddable_product(cls, bidding_round, cache) -> dict | None:
        round_product = bidding_round.products.select_related("product_type").first()
        if round_product is None:
            return None

        prices_by_product_id = {
            price.product_id: price
            for price in BiddingRoundProductPrice.objects.filter(
                round_product=round_product
            )
        }
        products = Product.objects.filter(
            type_id=round_product.product_type_id, deleted=False
        )
        serialized_products = []
        for product in products:
            price = prices_by_product_id.get(product.id)
            serialized_products.append(
                {
                    "id": product.id,
                    "name": product.name,
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
                }
            )
        return {
            "id": round_product.id,
            "product_type_id": round_product.product_type_id,
            "product_type_name": round_product.product_type.name,
            "products": serialized_products,
        }

    @classmethod
    def build_pickup_locations(cls, bidding_round, cache) -> list:
        product_type = None
        growing_period = None
        if bidding_round is not None:
            round_product = bidding_round.products.select_related(
                "product_type"
            ).first()
            if round_product is not None:
                product_type = round_product.product_type
            growing_period = bidding_round.growing_period

        utilization = {}
        if bidding_round is not None:
            utilization = (
                BiddingRoundStatsService.build_public_pickup_location_utilization(
                    bidding_round, cache=cache
                )
            )

        delivery_charge_reference_date = (
            growing_period.start_date if growing_period is not None else None
        )

        locations = list(PickupLocation.objects.prefetch_related("opening_times").all())
        serializer_context = {"cache": cache}
        if delivery_charge_reference_date is not None:
            serializer_context["reference_date_for_delivery_charge"] = (
                delivery_charge_reference_date
            )
        serialized_locations = list(
            PublicPickupLocationSerializer(
                locations, many=True, context=serializer_context
            ).data
        )

        result = []
        for location, serialized_location in zip(locations, serialized_locations):
            entry = dict(serialized_location)
            if product_type is not None and growing_period is not None:
                entry["yearly_delivery_charge"] = str(
                    BiddingRoundDeliveryChargeService.get_yearly_delivery_charge(
                        pickup_location_id=location.id,
                        product_type=product_type,
                        growing_period=growing_period,
                        cache=cache,
                    )
                )
            else:
                entry["yearly_delivery_charge"] = "0.00"
            if bidding_round is not None:
                entry["utilization"] = utilization.get(location.id)
            result.append(entry)
        return result

    @classmethod
    def build_bid_options(cls, cache) -> dict:
        return {
            "quantity_enabled": get_parameter_value(
                ParameterKeys.BIDDING_ROUND_BID_QUANTITY_ENABLED, cache=cache
            ),
            "multiple_positions_enabled": get_parameter_value(
                ParameterKeys.BIDDING_ROUND_BID_MULTIPLE_POSITIONS_ENABLED, cache=cache
            ),
        }

    @classmethod
    def parse_bool(cls, value):
        if value is None:
            return None
        return value.lower() in ("true", "1", "yes")

    @classmethod
    def is_membership_included_in_product_type(cls, cache) -> bool:
        try:
            return get_parameter_value(
                ParameterKeys.BIDDING_ROUND_STATS_MEMBERSHIP_INCLUDED_IN_PRODUCT_TYPE,
                cache=cache,
            )
        except KeyError:
            return False

    @classmethod
    def is_auto_renewal_enabled(cls, cache) -> bool:
        try:
            return bool(
                get_parameter_value(
                    ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=cache
                )
            )
        except KeyError:
            return False

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
    def has_manage_permission(cls, request) -> bool:
        return request.user.is_authenticated and request.user.has_perm(
            Permission.Coop.MANAGE
        )

    @classmethod
    def serialize_validation_error(cls, error: ValidationError) -> str:
        messages = getattr(error, "messages", None)
        if isinstance(messages, (list, tuple)):
            return "; ".join(str(message) for message in messages)
        return str(error)
