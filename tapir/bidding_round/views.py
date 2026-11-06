import csv
from decimal import Decimal

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from tapir.wirgarten.constants import Permission

from tapir.bidding_round.config import ACTIVE
from tapir.bidding_round.models import Bid, BiddingRound
from tapir.bidding_round.permissions import BiddingRoundFeatureFlagMixin
from tapir.bidding_round.serializers import (
    BidAdminSerializer,
    BidSerializer,
    BidSubmitSerializer,
    BiddingRoundCapacityCheckRequestSerializer,
    BiddingRoundCapacityCheckResponseSerializer,
    CheckContractsSerializer,
    ConfirmBidsSerializer,
    CreateContractsResponseSerializer,
    CreateContractsSerializer,
    GrowingPeriodOptionSerializer,
    LockAverageBidSerializer,
    MemberBidResponseSerializer,
    ProductTypeOptionSerializer,
    PublicDataResponseSerializer,
    PublicEvaluationResponseSerializer,
    RoundConfigSerializer,
    RoundCreateSerializer,
    RoundResultsResponseSerializer,
    RoundSerializer,
)
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.bidding_round_capacity_service import (
    BiddingRoundCapacityService,
)
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.bidding_round.services.bidding_round_view_service import (
    BiddingRoundViewService,
)
from tapir.bidding_round.services.contract_creator import ContractCreator
from tapir.bidding_round.services.contract_deletion_service import (
    BiddingRoundContractDeletionService,
)
from tapir.bestell_wizard.services.bestell_wizard_style_service import (
    BestellWizardStyleService,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.wirgarten.models import GrowingPeriod, Member, Product
from tapir.wirgarten.service.products import (
    get_next_growing_period,
    get_product_price,
)
from tapir.wirgarten.utils import get_now, get_today


def get_product_size(product, growing_period, cache):
    product_price = get_product_price(
        product=product, reference_date=growing_period.start_date, cache=cache
    )
    if product_price is None or not product_price.size:
        return None
    return product_price.size


def _sanitize_csv_cell(value) -> str:
    """Neutralises spreadsheet formula injection for text cells."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@"):
        return "'" + text
    return text


# --- Page views (React roots; the frontend apps land in Schritt 10) ---


class BiddingRoundView(TemplateView):
    template_name = "bidding_round/bidding_round.html"

    def get(self, request, *args, **kwargs):
        cache = {}
        if not BiddingRoundViewService.is_feature_flag_enabled(
            cache
        ) or not BiddingRoundViewService.is_public_url_enabled(cache):
            raise Http404
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        cache = {}
        context_data["body_style"] = BestellWizardStyleService.build_body_style(
            cache=cache
        )
        return context_data


class BiddingRoundConfigView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Coop.MANAGE
    template_name = "bidding_round/bidding_round_config.html"

    def dispatch(self, request, *args, **kwargs):
        cache = {}
        if not BiddingRoundViewService.is_feature_flag_enabled(cache):
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class BiddingRoundResultsView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Coop.MANAGE
    template_name = "bidding_round/bidding_round_results.html"

    def dispatch(self, request, *args, **kwargs):
        cache = {}
        if not BiddingRoundViewService.is_feature_flag_enabled(cache):
            raise Http404
        return super().dispatch(request, *args, **kwargs)


# --- Public API ---


class PublicDataView(BiddingRoundFeatureFlagMixin, APIView):
    require_public_url = True
    permission_classes = [AllowAny]

    @extend_schema(responses={200: PublicDataResponseSerializer})
    def get(self, request):
        cache = {}
        bidding_round = BiddingRoundService.get_current_open_round(cache=cache)
        pickup_location_change_enabled = (
            BiddingRoundService.is_pickup_location_change_enabled(cache=cache)
        )
        display_name = BiddingRoundViewService.get_display_name(cache)

        response_data = {
            "enabled": True,
            "url_enabled": BiddingRoundViewService.is_public_url_enabled(cache),
            "url": (
                request.build_absolute_uri(reverse("bidding_rounds:bidding_rounds"))
                if BiddingRoundViewService.is_public_url_enabled(cache)
                else None
            ),
            "display_name": display_name,
            "round": (
                BiddingRoundViewService.serialize_round(
                    bidding_round, cache, display_name
                )
                if bidding_round
                else None
            ),
            "round_status": "active" if bidding_round else "ended",
            "texts": BiddingRoundViewService.build_texts(cache),
            "biddable_product": (
                BiddingRoundViewService.build_biddable_product(bidding_round, cache)
                if bidding_round
                else None
            ),
            "pickup_locations": (
                BiddingRoundViewService.build_pickup_locations(bidding_round, cache)
                if pickup_location_change_enabled
                else []
            ),
            "bid_options": BiddingRoundViewService.build_bid_options(cache),
            "is_authenticated": request.user.is_authenticated,
            "current_pickup_location": None,
        }

        if bidding_round and request.user.is_authenticated:
            member = Member.objects.filter(id=request.user.id).first()
            if member:
                response_data["current_pickup_location_id"] = (
                    MemberPickupLocationGetter.get_member_pickup_location_id(
                        member=member,
                        reference_date=BiddingRoundCapacityService.get_contract_start_date(
                            bidding_round, cache
                        ),
                    )
                )
                response_data["current_pickup_location"] = (
                    BiddingRoundViewService.build_current_pickup_location(
                        bidding_round, member, cache
                    )
                )
                bid = Bid.objects.filter(round=bidding_round, member=member).first()
                if bid is not None:
                    response_data["bid"] = BiddingRoundViewService.serialize_bid(
                        bid,
                        BiddingRoundStatsService.get_default_position(
                            bidding_round, cache=cache
                        ),
                        cache,
                    )

        return Response(response_data, status=status.HTTP_200_OK)


class PublicResultsView(BiddingRoundFeatureFlagMixin, APIView):
    require_public_url = True
    permission_classes = [AllowAny]

    @extend_schema(responses={200: PublicEvaluationResponseSerializer})
    def get(self, request, round_id):
        cache = {}
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        if bidding_round.status != ACTIVE:
            raise Http404
        return Response(
            BiddingRoundStatsService.build_public_evaluation(
                bidding_round, cache=cache
            ),
            status=status.HTTP_200_OK,
        )


class BiddingRoundCapacityCheckThrottle(AnonRateThrottle):
    rate = "120/min"


class BiddingRoundCapacityCheckUserThrottle(UserRateThrottle):
    rate = "240/min"


class BiddingRoundCapacityCheckView(BiddingRoundFeatureFlagMixin, APIView):
    require_public_url = True
    permission_classes = [IsAuthenticated]
    throttle_classes = [
        BiddingRoundCapacityCheckThrottle,
        BiddingRoundCapacityCheckUserThrottle,
    ]

    @extend_schema(
        request=BiddingRoundCapacityCheckRequestSerializer,
        responses={200: BiddingRoundCapacityCheckResponseSerializer},
    )
    def post(self, request, round_id):
        cache = {}
        bidding_round = BiddingRoundService.get_current_open_round(cache=cache)
        if bidding_round is None or str(bidding_round.id) != str(round_id):
            raise Http404

        serializer = BiddingRoundCapacityCheckRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        member = Member.objects.filter(id=request.user.id).first()
        if member is None:
            return Response(status=status.HTTP_403_FORBIDDEN)

        reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
            bidding_round=bidding_round,
            items=validated.get("items", []),
            pickup_location_id=validated.get("pickup_location_id"),
            member=member,
            cache=cache,
        )
        return Response(
            {
                "sufficient": not reasons,
                "message": (
                    BiddingRoundCapacityService.build_insufficient_capacity_message(
                        reasons
                    )
                    if reasons
                    else ""
                ),
            },
            status=status.HTTP_200_OK,
        )


# --- Admin API ---


class RoundListCreateView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(responses={200: RoundSerializer(many=True)})
    def get(self, request):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        rounds = BiddingRound.objects.annotate(
            has_bids=Exists(Bid.objects.filter(round=OuterRef("pk")))
        ).order_by("-created_at")
        display_name = BiddingRoundViewService.get_display_name(cache)
        return Response(
            [
                BiddingRoundViewService.serialize_round(
                    bidding_round, cache, display_name
                )
                for bidding_round in rounds
            ],
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={201: RoundSerializer}, request=RoundCreateSerializer())
    def post(self, request):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = RoundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        growing_period_id = validated.get("growing_period_id")
        if growing_period_id:
            growing_period = get_object_or_404(GrowingPeriod, id=growing_period_id)
        else:
            growing_period = get_next_growing_period()
            if growing_period is None:
                return Response(
                    {
                        "error": _(
                            "Für die Beitragsrunde gibt es keine passende Saison."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        try:
            bidding_round = BiddingRoundService.create_round(
                growing_period=growing_period,
                name=validated["name"],
                bidding_procedure=validated["bidding_procedure"],
                end_at=validated["end_at"],
                start_at=validated.get("start_at"),
                include_auto_renewed=validated.get("include_auto_renewed"),
                comment=validated.get("comment", ""),
                product_type_id=validated.get("product_type_id"),
                bid_levels=validated.get("bid_levels", 1),
                target_amount_per_year=validated.get("target_amount_per_year"),
                prices=validated.get("prices"),
                cache=cache,
            )
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            BiddingRoundViewService.serialize_round(bidding_round, cache),
            status=status.HTTP_201_CREATED,
        )


class GrowingPeriodsView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(responses={200: GrowingPeriodOptionSerializer(many=True)})
    def get(self, request):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        periods = GrowingPeriod.objects.filter(
            end_date__gte=get_today(cache=cache)
        ).order_by("start_date")
        return Response(
            [
                {
                    "id": period.id,
                    "start_date": period.start_date.isoformat(),
                    "end_date": period.end_date.isoformat(),
                }
                for period in periods
            ],
            status=status.HTTP_200_OK,
        )


class AvailableProductTypesView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(
        responses={200: ProductTypeOptionSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="growing_period_id",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
            )
        ],
    )
    def get(self, request):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        growing_period_id = request.query_params.get("growing_period_id")
        if growing_period_id:
            growing_period = get_object_or_404(GrowingPeriod, id=growing_period_id)
        else:
            growing_period = get_next_growing_period()
        if growing_period is None:
            return Response([], status=status.HTTP_200_OK)
        product_types = BiddingRoundService.get_product_types_with_capacity_for_period(
            growing_period, cache=cache
        )
        return Response(
            [
                {
                    "id": product_type.id,
                    "name": product_type.name,
                    "products": [
                        {
                            "id": product.id,
                            "name": product.name,
                            "size": get_product_size(product, growing_period, cache),
                        }
                        for product in Product.objects.filter(
                            type_id=product_type.id, deleted=False
                        )
                    ],
                }
                for product_type in product_types
            ],
            status=status.HTTP_200_OK,
        )


class RoundDetailView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(responses={200: RoundSerializer})
    def get(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        return Response(
            BiddingRoundViewService.serialize_round(bidding_round, cache),
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={200: RoundSerializer}, request=RoundConfigSerializer())
    def patch(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        serializer = RoundConfigSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            BiddingRoundService.update_round_config(
                bidding_round, serializer.validated_data, cache=cache
            )
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            BiddingRoundViewService.serialize_round(bidding_round, cache),
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        try:
            BiddingRoundService.delete_round(bidding_round, cache=cache)
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoundStartView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(request=None, responses={200: RoundSerializer})
    def post(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        try:
            BiddingRoundService.start_round(bidding_round, cache=cache)
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            BiddingRoundViewService.serialize_round(bidding_round, cache),
            status=status.HTTP_200_OK,
        )


class RoundCloseView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(request=None, responses={200: RoundSerializer})
    def post(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        try:
            BiddingRoundService.close_round(bidding_round, cache=cache)
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            BiddingRoundViewService.serialize_round(bidding_round, cache),
            status=status.HTTP_200_OK,
        )


class RoundReopenView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(request=None, responses={200: RoundSerializer})
    def post(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        try:
            BiddingRoundService.reopen_round(bidding_round, cache=cache)
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            BiddingRoundViewService.serialize_round(bidding_round, cache),
            status=status.HTTP_200_OK,
        )


class RoundResultsView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(
        responses={200: RoundResultsResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="include_auto_renewed",
                type=bool,
                required=False,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="traffic_light_position",
                type=float,
                required=False,
                location=OpenApiParameter.QUERY,
                description="Position auf der Solidaritätsachse: 0 (grün) … 50 (zufrieden) … 100 (rot).",
            ),
            OpenApiParameter(
                name="filter",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="sort",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
            ),
        ],
    )
    def get(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)

        include_auto_renewed = BiddingRoundViewService.parse_bool(
            request.query_params.get("include_auto_renewed")
        )
        membership_included_in_product_type = (
            BiddingRoundViewService.is_membership_included_in_product_type(cache)
        )
        default_position = BiddingRoundStatsService.get_default_position(
            bidding_round,
            cache=cache,
            membership_included_in_product_type=membership_included_in_product_type,
        )
        traffic_light_position = request.query_params.get("traffic_light_position")
        if traffic_light_position is None:
            traffic_light_position = default_position
        recommended_level = BiddingRoundStatsService.build_recommended_level(
            bidding_round,
            cache=cache,
            membership_included_in_product_type=membership_included_in_product_type,
        )
        extra_positions = BiddingRoundStatsService.build_extra_positions(
            bidding_round,
            cache=cache,
            membership_included_in_product_type=membership_included_in_product_type,
        )
        stats = BiddingRoundStatsService.build_stats(
            bidding_round,
            include_auto_renewed=include_auto_renewed,
            traffic_light_position=traffic_light_position,
            cache=cache,
        )

        results_table = BiddingRoundStatsService.build_results_table(
            bidding_round, cache=cache
        )
        members = [
            {
                "member_id": entry["member"].id,
                "member_name": f"{entry['member'].first_name} {entry['member'].last_name}",
                "member_email": entry["member"].email,
                "has_bid": entry["has_bid"],
                "is_active_in_contract_period": entry["is_active_in_contract_period"],
                "is_auto_renewed": entry["is_auto_renewed"],
                "auto_renewed_items": entry["auto_renewed_items"],
                "auto_renewed_pickup_location_name": entry.get(
                    "auto_renewed_pickup_location_name"
                ),
                "auto_renewed_amount_per_year": entry["auto_renewed_amount_per_year"],
                "auto_renewed_amount_per_month": entry["auto_renewed_amount_per_month"],
                "bid": BiddingRoundViewService.serialize_bid(
                    entry["bid"], default_position, cache
                ),
            }
            for entry in results_table["members"]
        ]
        results_table["members"] = BiddingRoundViewService.filter_and_sort_members(
            members,
            filter_=request.query_params.get("filter", "all"),
            sort=request.query_params.get("sort", "name"),
        )
        if "pickup_locations" in results_table:
            results_table["pickup_locations"] = [
                {
                    "pickup_location_id": entry["pickup_location"].id,
                    "pickup_location_name": entry["pickup_location"].name,
                    "capacity": entry["capacity"],
                    "demand": entry["demand"],
                    "fill_percent": entry["fill_percent"],
                }
                for entry in results_table["pickup_locations"]
            ]
        extra_reached_per_year = sum(
            (
                position["reached_per_year"]
                for position in extra_positions.values()
                if position["applicable"]
            ),
            Decimal("0"),
        )
        return Response(
            {
                "display_name": BiddingRoundViewService.get_display_name(cache),
                "stats": stats,
                "totals": BiddingRoundStatsService.build_totals(
                    stats, extra_reached_per_year=extra_reached_per_year
                ),
                "extra_positions": extra_positions,
                "average_bid": BiddingRoundStatsService.build_average_bid(
                    bidding_round, cache=cache
                ),
                "include_auto_renewed": bidding_round.include_auto_renewed,
                "auto_renewed_enabled": (
                    bidding_round.include_auto_renewed
                    and BiddingRoundViewService.is_auto_renewal_enabled(cache)
                ),
                "bidding_procedure": bidding_round.bidding_procedure,
                "bid_levels": bidding_round.bid_levels,
                "recommended_level": recommended_level,
                "traffic_light_position": float(traffic_light_position),
                "financing_projection": BiddingRoundStatsService.build_financing_projection(
                    bidding_round,
                    cache=cache,
                    include_auto_renewed=include_auto_renewed is not False,
                    membership_included_in_product_type=(
                        membership_included_in_product_type
                    ),
                ),
                "results_table": results_table,
                "biddable_product": BiddingRoundViewService.build_biddable_product(
                    bidding_round, cache
                ),
                "pickup_locations": (
                    BiddingRoundViewService.build_pickup_locations(bidding_round, cache)
                    if BiddingRoundService.is_pickup_location_change_enabled(
                        cache=cache
                    )
                    else []
                ),
                "bid_options": BiddingRoundViewService.build_bid_options(cache),
                "contracts_created_at": bidding_round.contracts_created_at,
                "average_bid_locked_at": bidding_round.average_bid_locked_at,
                "locked_traffic_light_position": (
                    bidding_round.locked_traffic_light_position
                ),
                "locked_average_bid_per_share_per_month": (
                    bidding_round.locked_average_bid_per_share_per_month
                ),
                "locked_average_bid_per_share_per_year": (
                    bidding_round.locked_average_bid_per_share_per_year
                ),
                "locked_bidder_average_per_share_per_month": (
                    bidding_round.locked_bidder_average_per_share_per_month
                ),
                "locked_bidder_average_per_share_per_year": (
                    bidding_round.locked_bidder_average_per_share_per_year
                ),
                "locked_surcharge_percent": bidding_round.locked_surcharge_percent,
                "locked_surcharge_on_bids": bidding_round.locked_surcharge_on_bids,
                "locked_surcharge_on_average": (
                    bidding_round.locked_surcharge_on_average
                ),
                "contracts": BiddingRoundViewService.serialize_contracts(
                    bidding_round, cache, position=default_position
                ),
                "growing_period_id": bidding_round.growing_period_id,
            },
            status=status.HTTP_200_OK,
        )


class BidCreateView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(responses={201: BidSerializer}, request=BidAdminSerializer())
    def post(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        serializer = BidAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        member_id = validated.get("member_id")
        if not member_id:
            return Response(
                {"error": _("Es muss ein Mitglied ausgewählt werden.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Bid.objects.filter(round=bidding_round, member_id=member_id).exists():
            return Response(
                {"error": _("Für dieses Mitglied existiert bereits ein Gebot.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member = get_object_or_404(Member, id=member_id)
        try:
            bid = BiddingRoundService.save_admin_bid(
                bidding_round=bidding_round,
                member=member,
                items=validated.get("items"),
                pickup_location_id=validated.get("pickup_location_id"),
                entered_by_admin=True,
                admin_confirmed=validated.get("admin_confirmed", False),
                cache=cache,
            )
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            BiddingRoundViewService.serialize_bid(
                bid,
                BiddingRoundStatsService.get_default_position(
                    bidding_round, cache=cache
                ),
                cache,
            ),
            status=status.HTTP_201_CREATED,
        )


class BidEditView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(responses={200: BidSerializer}, request=BidAdminSerializer())
    def patch(self, request, round_id, bid_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bid = get_object_or_404(Bid, id=bid_id, round_id=round_id)
        serializer = BidAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        try:
            bid = BiddingRoundService.save_admin_bid(
                bidding_round=bid.round,
                member=bid.member,
                items=validated.get("items"),
                pickup_location_id=validated.get(
                    "pickup_location_id", bid.pickup_location_id
                ),
                entered_by_admin=validated.get("entered_by_admin"),
                admin_confirmed=validated.get("admin_confirmed"),
                cache=cache,
            )
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            BiddingRoundViewService.serialize_bid(
                bid,
                BiddingRoundStatsService.get_default_position(bid.round, cache=cache),
                cache,
            ),
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={204: None})
    def delete(self, request, round_id, bid_id):
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bid = get_object_or_404(Bid, id=bid_id, round_id=round_id)
        if bid.round.contracts_created_at is not None:
            return Response(
                {
                    "error": _(
                        "Gebote können nicht mehr gelöscht werden, nachdem die Verträge erstellt wurden."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        bid.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConfirmBidsView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(
        responses={200: BidSerializer(many=True)}, request=ConfirmBidsSerializer()
    )
    def post(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        serializer = ConfirmBidsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bid_ids = serializer.validated_data.get("bid_ids", [])
        bids = bidding_round.bids
        if bid_ids:
            bids = bids.filter(id__in=bid_ids)
        bids.update(admin_confirmed=get_now())
        effective_position = BiddingRoundStatsService.get_default_position(
            bidding_round, cache=cache
        )
        return Response(
            [
                BiddingRoundViewService.serialize_bid(bid, effective_position, cache)
                for bid in bidding_round.bids.prefetch_related(
                    "items__product",
                    "items__round_product__product_type",
                    "pickup_location",
                )
            ],
            status=status.HTTP_200_OK,
        )


class CreateContractsView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(
        responses={200: CreateContractsResponseSerializer},
        request=CreateContractsSerializer(),
    )
    def post(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        serializer = CreateContractsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = ContractCreator.create_contracts_from_bids(
                bidding_round,
                bid_ids=serializer.validated_data.get("bid_ids"),
                bid_level=serializer.validated_data.get("bid_level"),
                create_auto_renewed_contracts=serializer.validated_data.get(
                    "create_auto_renewed_contracts", False
                ),
                auto_renewed_member_ids=serializer.validated_data.get(
                    "auto_renewed_member_ids"
                ),
                actor=request.user,
                cache=cache,
            )
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "errors": [
                    {
                        "bid_id": entry["bid_id"],
                        "member_id": entry["member"].id,
                        "member_name": f"{entry['member'].first_name} {entry['member'].last_name}",
                        "product_name": entry.get("product_name", ""),
                        "error": entry["error"],
                    }
                    for entry in result["errors"]
                ],
                "subscriptions": [
                    {
                        "id": subscription.id,
                        "member_id": subscription.member_id,
                        "product_id": subscription.product_id,
                    }
                    for subscription in result["subscriptions"]
                ],
            },
            status=status.HTTP_200_OK,
        )


class RoundLockAverageBidView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(responses={200: RoundSerializer}, request=LockAverageBidSerializer())
    def post(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        serializer = LockAverageBidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            BiddingRoundService.lock_average_bid(
                bidding_round=bidding_round,
                position=serializer.validated_data["position"],
                surcharge_percent=serializer.validated_data.get("surcharge_percent", 0),
                surcharge_on_bids=serializer.validated_data.get(
                    "surcharge_on_bids", False
                ),
                surcharge_on_average=serializer.validated_data.get(
                    "surcharge_on_average", False
                ),
                cache=cache,
            )
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            BiddingRoundViewService.serialize_round(bidding_round, cache),
            status=status.HTTP_200_OK,
        )


class RoundUnlockAverageBidView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(responses={200: RoundSerializer})
    def post(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        try:
            BiddingRoundService.unlock_average_bid(bidding_round, cache=cache)
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            BiddingRoundViewService.serialize_round(bidding_round, cache),
            status=status.HTTP_200_OK,
        )


class RoundDeleteContractsView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(responses={200: RoundSerializer})
    def post(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        try:
            BiddingRoundContractDeletionService.delete_contracts(
                bidding_round, actor=request.user, cache=cache
            )
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            BiddingRoundViewService.serialize_round(bidding_round, cache),
            status=status.HTTP_200_OK,
        )


class RoundCheckContractsView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(
        responses={200: CreateContractsResponseSerializer},
        request=CheckContractsSerializer(),
    )
    def post(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        serializer = CheckContractsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        errors = ContractCreator.check_contracts_from_bids(
            bidding_round,
            cache=cache,
            bid_ids=serializer.validated_data.get("bid_ids"),
        )
        return Response(
            {
                "errors": [
                    {
                        "bid_id": entry["bid_id"],
                        "member_id": entry["member"].id,
                        "member_name": f"{entry['member'].first_name} {entry['member'].last_name}",
                        "product_name": entry.get("product_name", ""),
                        "error": entry["error"],
                    }
                    for entry in errors
                ],
                "subscriptions": [],
            },
            status=status.HTTP_200_OK,
        )


class ExportCsvView(BiddingRoundFeatureFlagMixin, APIView):
    @extend_schema(responses={200: str})
    def get(self, request, round_id):
        cache = {}
        if not BiddingRoundViewService.has_manage_permission(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="bidding_round_{bidding_round.id}.csv"'
        )
        # UTF-8 BOM so Excel detects the encoding.
        response.write("\ufeff")
        writer = csv.writer(response, delimiter=";")
        writer.writerow(
            [
                _("Mitglied"),
                _("E-Mail"),
                _("Produkttyp"),
                _("Produkt"),
                _("Anteile"),
                _("Betrag (effektive Stufe)"),
                _("Abholort"),
            ]
        )
        effective_position = BiddingRoundStatsService.get_default_position(
            bidding_round, cache=cache
        )
        for bid in bidding_round.bids.select_related(
            "member", "pickup_location"
        ).prefetch_related("items__product", "items__round_product__product_type"):
            for item in bid.items.select_related(
                "product", "round_product__product_type"
            ):
                writer.writerow(
                    [
                        _sanitize_csv_cell(
                            f"{bid.member.first_name} {bid.member.last_name}"
                        ),
                        _sanitize_csv_cell(bid.member.email),
                        _sanitize_csv_cell(item.round_product.product_type.name),
                        _sanitize_csv_cell(item.product.name),
                        item.quantity,
                        BiddingRoundStatsService.get_effective_amount(
                            item,
                            bidding_round,
                            position=effective_position,
                            cache=cache,
                        ),
                        _sanitize_csv_cell(
                            bid.pickup_location.name if bid.pickup_location else ""
                        ),
                    ]
                )
        return response


# --- Member API ---


class MemberBidView(BiddingRoundFeatureFlagMixin, APIView):
    require_public_url = True
    permission_classes = [AllowAny]

    def _get_member(self, request):
        if not request.user.is_authenticated:
            return None
        return Member.objects.filter(id=request.user.id).first()

    @extend_schema(responses={200: MemberBidResponseSerializer})
    def get(self, request, round_id):
        cache = {}
        member = self._get_member(request)
        if not member:
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        bid = Bid.objects.filter(round=bidding_round, member=member).first()
        return Response(
            {
                "round": BiddingRoundViewService.serialize_round(bidding_round, cache),
                "biddable_product": BiddingRoundViewService.build_biddable_product(
                    bidding_round, cache
                ),
                "pickup_locations": (
                    BiddingRoundViewService.build_pickup_locations(bidding_round, cache)
                    if BiddingRoundService.is_pickup_location_change_enabled(
                        cache=cache
                    )
                    else []
                ),
                "current_pickup_location": (
                    BiddingRoundViewService.build_current_pickup_location(
                        bidding_round, member, cache
                    )
                ),
                "bid": (
                    BiddingRoundViewService.serialize_bid(
                        bid,
                        BiddingRoundStatsService.get_default_position(
                            bidding_round, cache=cache
                        ),
                        cache,
                    )
                    if bid is not None
                    else None
                ),
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={200: str}, request=BidSubmitSerializer())
    def post(self, request, round_id):
        cache = {}
        member = self._get_member(request)
        if not member:
            return Response(status=status.HTTP_403_FORBIDDEN)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        serializer = BidSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        try:
            BiddingRoundService.save_bid(
                member,
                bidding_round,
                validated["items"],
                pickup_location_id=validated.get("pickup_location_id"),
                cache=cache,
            )
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response("OK", status=status.HTTP_200_OK)
