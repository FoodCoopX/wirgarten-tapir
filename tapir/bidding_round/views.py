from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.bestell_wizard.services.bestell_wizard_style_service import (
    BestellWizardStyleService,
)
from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_SIMPLE,
    BIDDING_ROUND_STATUS_ACTIVE,
)
from tapir.bidding_round.models import Bid, BiddingRound
from tapir.bidding_round.permissions import (
    BiddingRoundCacheMixin,
    BiddingRoundFeatureFlagMixin,
    BiddingRoundManagePermission,
)
from tapir.bidding_round.serializers import (
    BidSubmitSerializer,
    CreateContractsResponseSerializer,
    CreateContractsSerializer,
    GrowingPeriodOptionSerializer,
    MemberBidResponseSerializer,
    ProductTypeOptionSerializer,
    PublicDataResponseSerializer,
    PublicEvaluationResponseSerializer,
    RoundConfigSerializer,
    RoundCreateSerializer,
    RoundResultsResponseSerializer,
    RoundSerializer,
)
from tapir.bidding_round.services.bid_input import BidInput
from tapir.bidding_round.services.bidding_round_service import (
    BiddingRoundConfigChanges,
    BiddingRoundService,
    RoundPriceInput,
)
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.bidding_round.services.bidding_round_view_service import (
    BiddingRoundViewService,
)
from tapir.bidding_round.services.contract_creator import ContractCreator
from tapir.bidding_round.services.product_size_service import ProductSizeService
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import GrowingPeriod, Member, Product
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.utils import get_today


class BiddingRoundView(BiddingRoundCacheMixin, TemplateView):
    template_name = "bidding_round/bidding_round.html"

    def get(self, request, *args, **kwargs):
        if not BiddingRoundViewService.is_feature_flag_enabled(
            self.cache
        ) or not BiddingRoundViewService.is_public_url_enabled(self.cache):
            raise Http404
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["body_style"] = BestellWizardStyleService.build_body_style(
            cache=self.cache
        )
        return context_data


class BiddingRoundConfigView(
    BiddingRoundCacheMixin, PermissionRequiredMixin, TemplateView
):
    permission_required = Permission.Coop.MANAGE
    template_name = "bidding_round/bidding_round_config.html"

    def dispatch(self, request, *args, **kwargs):
        if not BiddingRoundViewService.is_feature_flag_enabled(self.cache):
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class BiddingRoundResultsView(
    BiddingRoundCacheMixin, PermissionRequiredMixin, TemplateView
):
    permission_required = Permission.Coop.MANAGE
    template_name = "bidding_round/bidding_round_results.html"

    def dispatch(self, request, *args, **kwargs):
        if not BiddingRoundViewService.is_feature_flag_enabled(self.cache):
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class PublicDataView(BiddingRoundFeatureFlagMixin, APIView):
    require_public_url = True
    permission_classes = [AllowAny]

    @extend_schema(responses={200: PublicDataResponseSerializer})
    def get(self, request):
        cache = self.cache
        bidding_round = BiddingRoundService.get_current_open_round(cache=cache)
        member = None
        if request.user.is_authenticated:
            member = Member.objects.filter(id=request.user.id).first()

        response_data = {
            "enabled": True,
            "url_enabled": BiddingRoundViewService.is_public_url_enabled(cache),
            "url": (
                request.build_absolute_uri(reverse("bidding_rounds:bidding_rounds"))
                if BiddingRoundViewService.is_public_url_enabled(cache)
                else None
            ),
            "round": (
                BiddingRoundViewService.serialize_round(bidding_round, cache)
                if bidding_round
                else None
            ),
            "round_status": "active" if bidding_round else "ended",
            "texts": BiddingRoundViewService.build_texts(cache),
            "biddable_product": (
                BiddingRoundViewService.build_biddable_product(
                    bidding_round, cache, member=member
                )
                if bidding_round
                else None
            ),
            "is_authenticated": request.user.is_authenticated,
        }

        if bidding_round and member:
            bid = Bid.objects.filter(round=bidding_round, member=member).first()
            if bid is not None:
                response_data["bid"] = BiddingRoundViewService.serialize_bid(
                    bid, cache=cache
                )

        return Response(response_data, status=status.HTTP_200_OK)


class PublicResultsView(BiddingRoundFeatureFlagMixin, APIView):
    require_public_url = True
    permission_classes = [AllowAny]

    @extend_schema(responses={200: PublicEvaluationResponseSerializer})
    def get(self, request, round_id):
        cache = {}
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        if bidding_round.status != BIDDING_ROUND_STATUS_ACTIVE:
            raise Http404
        return Response(
            BiddingRoundStatsService.build_public_evaluation(bidding_round, cache),
            status=status.HTTP_200_OK,
        )


class RoundListCreateView(BiddingRoundFeatureFlagMixin, APIView):
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(responses={200: RoundSerializer(many=True)})
    def get(self, request):
        cache = self.cache
        rounds = BiddingRound.objects.annotate(
            has_bids=Exists(Bid.objects.filter(round=OuterRef("pk")))
        ).order_by("-created_at")
        return Response(
            [
                BiddingRoundViewService.serialize_round(bidding_round, cache)
                for bidding_round in rounds
            ],
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={201: RoundSerializer}, request=RoundCreateSerializer())
    def post(self, request):
        cache = self.cache
        serializer = RoundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        growing_period_id = validated.get("growing_period_id")
        if growing_period_id:
            growing_period = get_object_or_404(GrowingPeriod, id=growing_period_id)
        else:
            growing_period = TapirCache.get_first_growing_period_starting_after(
                reference_date=get_today(cache=cache), cache=cache
            )
            if growing_period is None:
                return Response(
                    {
                        "error": _(
                            "Für die Beitragsrunde gibt es keine passende Saison."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        product_type_id = validated.get("product_type_id")
        if not product_type_id:
            product_types = (
                BiddingRoundService.get_product_types_with_capacity_for_period(
                    growing_period
                )
            )
            if len(product_types) != 1:
                return Response(
                    {"error": _("Bitte genau einen Produkttyp auswählen.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            product_type_id = product_types[0].id
        bidding_procedure = validated.get(
            "bidding_procedure", BIDDING_ROUND_PROCEDURE_SIMPLE
        )
        bid_levels = validated.get("bid_levels", 1)
        try:
            with transaction.atomic():
                BiddingRoundService.validate_round_creation(
                    end_at=validated["end_at"],
                    start_at=validated.get("start_at"),
                    bidding_procedure=bidding_procedure,
                    bid_levels=bid_levels,
                )
                bidding_round = BiddingRoundService.create_round(
                    growing_period=growing_period,
                    name=validated["name"],
                    end_at=validated["end_at"],
                    start_at=validated.get("start_at"),
                    comment=validated.get("comment", ""),
                    product_type_id=product_type_id,
                    target_amount_per_year=validated.get("target_amount_per_year"),
                    prices=(
                        [
                            RoundPriceInput.from_mapping(price)
                            for price in validated["prices"]
                        ]
                        if "prices" in validated
                        else None
                    ),
                    bidding_procedure=bidding_procedure,
                    bid_levels=bid_levels,
                    include_auto_renewed=validated.get("include_auto_renewed", True),
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
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(responses={200: GrowingPeriodOptionSerializer(many=True)})
    def get(self, request):
        cache = self.cache
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
    permission_classes = [BiddingRoundManagePermission]

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
        cache = self.cache
        growing_period_id = request.query_params.get("growing_period_id")
        if growing_period_id:
            growing_period = get_object_or_404(GrowingPeriod, id=growing_period_id)
        else:
            growing_period = TapirCache.get_first_growing_period_starting_after(
                reference_date=get_today(cache=cache), cache=cache
            )
        if growing_period is None:
            return Response([], status=status.HTTP_200_OK)
        product_types = BiddingRoundService.get_product_types_with_capacity_for_period(
            growing_period
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
                            "size": ProductSizeService.get_size(
                                product, growing_period, cache
                            ),
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
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(responses={200: RoundSerializer})
    def get(self, request, round_id):
        cache = self.cache
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        return Response(
            BiddingRoundViewService.serialize_round(bidding_round, cache),
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={200: RoundSerializer}, request=RoundConfigSerializer())
    def patch(self, request, round_id):
        cache = self.cache
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        serializer = RoundConfigSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            BiddingRoundService.update_round_config(
                bidding_round,
                BiddingRoundConfigChanges.from_mapping(serializer.validated_data),
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

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, round_id):
        cache = self.cache
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
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(request=None, responses={200: RoundSerializer})
    def post(self, request, round_id):
        cache = self.cache
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
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(request=None, responses={200: RoundSerializer})
    def post(self, request, round_id):
        cache = self.cache
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
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(request=None, responses={200: RoundSerializer})
    def post(self, request, round_id):
        cache = self.cache
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
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(
        responses={200: RoundResultsResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="position",
                type=float,
                required=False,
                location=OpenApiParameter.QUERY,
            )
        ],
    )
    def get(self, request, round_id):
        cache = self.cache
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        position = request.query_params.get("position")
        return Response(
            BiddingRoundStatsService.build_admin_evaluation(
                bidding_round, cache, position=position
            ),
            status=status.HTTP_200_OK,
        )


class MemberBidView(BiddingRoundFeatureFlagMixin, APIView):
    require_public_url = True
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _get_member(request) -> Member | None:
        return Member.objects.filter(id=request.user.id).first()

    @staticmethod
    def _require_member(request) -> Member:
        member = MemberBidView._get_member(request)
        if member is None:
            raise PermissionDenied(_("Für dieses Konto gibt es kein Mitglied."))
        return member

    @extend_schema(responses={200: MemberBidResponseSerializer})
    def get(self, request, round_id):
        cache = self.cache
        member = self._require_member(request)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        bid = Bid.objects.filter(round=bidding_round, member=member).first()
        return Response(
            {
                "round": BiddingRoundViewService.serialize_round(bidding_round, cache),
                "biddable_product": BiddingRoundViewService.build_biddable_product(
                    bidding_round, cache, member=member
                ),
                "bid": (
                    BiddingRoundViewService.serialize_bid(bid, cache=cache)
                    if bid is not None
                    else None
                ),
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=BidSubmitSerializer(), responses={200: None})
    def post(self, request, round_id):
        cache = self.cache
        member = self._require_member(request)
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        serializer = BidSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            BiddingRoundService.save_bid(
                member,
                bidding_round,
                BidInput.from_mapping(serializer.validated_data),
                cache=cache,
            )
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response("OK", status=status.HTTP_200_OK)


class CreateContractsView(BiddingRoundFeatureFlagMixin, APIView):
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(
        responses={200: CreateContractsResponseSerializer},
        request=CreateContractsSerializer(),
    )
    def post(self, request, round_id):
        cache = self.cache
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
                        "member_id": entry.member.id,
                        "member_name": str(entry.member),
                        "error": entry.error,
                    }
                    for entry in result.errors
                ],
                "subscriptions": [
                    {
                        "id": subscription.id,
                        "member_id": subscription.member_id,
                        "product_id": subscription.product_id,
                    }
                    for subscription in result.subscriptions
                ],
            },
            status=status.HTTP_200_OK,
        )
