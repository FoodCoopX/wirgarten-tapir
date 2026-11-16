from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
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
    BiddingRoundFeatureFlagMixin,
    BiddingRoundManagePermission,
)
from tapir.bidding_round.serializers import (
    BidAdminCreateSerializer,
    BidAdminSerializer,
    BidSerializer,
    BidSubmitSerializer,
    ConfirmBidsSerializer,
    CreateContractsResponseSerializer,
    CreateContractsSerializer,
    GrowingPeriodOptionSerializer,
    LockAverageBidSerializer,
    MemberBidResponseSerializer,
    MemberOptionSerializer,
    ProductTypeOptionSerializer,
    PublicDataResponseSerializer,
    PublicEvaluationResponseSerializer,
    RoundConfigSerializer,
    RoundCreateSerializer,
    RoundResultsResponseSerializer,
    RoundSerializer,
)
from tapir.bidding_round.services.bidding_round_csv_export_service import (
    BiddingRoundCsvExportService,
)
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.bidding_round.services.bidding_round_view_service import (
    BiddingRoundViewService,
)
from tapir.bidding_round.services.contract_creator import ContractCreator
from tapir.bidding_round.services.product_size_service import ProductSizeService
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import GrowingPeriod, Member, Product, Subscription
from tapir.wirgarten.service.products import get_next_growing_period
from tapir.wirgarten.utils import get_today


class BiddingRoundView(TemplateView):
    template_name = "bidding_round/bidding_round.html"

    def get(self, request, *args, **kwargs):
        cache = {}
        if not BiddingRoundViewService.is_feature_flag_enabled(cache):
            raise Http404
        if not BiddingRoundViewService.public_access_allowed(request.user, cache):
            return redirect_to_login(request.get_full_path())
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


class PublicDataView(BiddingRoundFeatureFlagMixin, APIView):
    require_public_url = True
    permission_classes = [AllowAny]

    @extend_schema(responses={200: PublicDataResponseSerializer})
    def get(self, request):
        cache = {}
        bidding_round = BiddingRoundService.get_current_open_round(cache=cache)
        display_name = BiddingRoundViewService.get_display_name(cache)
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
                BiddingRoundViewService.build_biddable_product(
                    bidding_round, cache, member=member
                )
                if bidding_round
                else None
            ),
            "is_authenticated": request.user.is_authenticated,
            "status_enabled": BiddingRoundViewService.is_status_enabled(cache),
            "status_public_enabled": BiddingRoundViewService.is_status_public_enabled(
                cache
            ),
            "bid_options": BiddingRoundViewService.build_bid_options(cache),
            "sepa_enabled": BiddingRoundViewService.is_sepa_enabled(cache),
            "feedback_enabled": BiddingRoundViewService.is_feedback_enabled(cache),
            "first_name": member.first_name if member is not None else None,
            "association_membership": None,
        }

        if bidding_round and member:
            response_data.update(
                BiddingRoundViewService.build_member_data(member, bidding_round, cache)
            )
            response_data["current_pickup_location"] = (
                BiddingRoundViewService.build_current_pickup_location(
                    bidding_round, member, cache
                )
            )
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
        if not BiddingRoundViewService.is_status_enabled(cache):
            raise Http404
        if (
            not BiddingRoundViewService.is_status_public_enabled(cache)
            and not request.user.is_authenticated
        ):
            raise Http404
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
        cache = {}
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
                end_at=validated["end_at"],
                start_at=validated.get("start_at"),
                comment=validated.get("comment", ""),
                product_type_id=validated.get("product_type_id"),
                target_amount_per_year=validated.get("target_amount_per_year"),
                prices=validated.get("prices"),
                bidding_procedure=validated.get(
                    "bidding_procedure", BIDDING_ROUND_PROCEDURE_SIMPLE
                ),
                bid_levels=validated.get("bid_levels", 1),
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
        cache = {}
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
        cache = {}
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
        cache = {}
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        return Response(
            BiddingRoundViewService.serialize_round(bidding_round, cache),
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={200: RoundSerializer}, request=RoundConfigSerializer())
    def patch(self, request, round_id):
        cache = {}
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
        cache = {}
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
        cache = {}
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
        cache = {}
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
        cache = {}
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
    permission_classes = [AllowAny]

    @staticmethod
    def _get_member(request):
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
                cache=cache,
                sepa_allowed=validated.get("sepa_allowed", False),
                account_owner=validated.get("account_owner"),
                iban=validated.get("iban"),
                payment_rhythm=validated.get("payment_rhythm"),
                privacy_policy_read=validated.get("privacy_policy_read", False),
                cancellation_policy_read=validated.get(
                    "cancellation_policy_read", False
                ),
                contract_accepted=validated.get("contract_accepted", False),
                enforce_consents=True,
                feedback=validated.get("feedback"),
            )
        except ValidationError as error:
            return Response(
                {"error": BiddingRoundViewService.serialize_validation_error(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response("OK", status=status.HTTP_200_OK)


class BidCreateView(BiddingRoundFeatureFlagMixin, APIView):
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(responses={201: BidSerializer}, request=BidAdminCreateSerializer())
    def post(self, request, round_id):
        cache = {}
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        serializer = BidAdminCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        member_id = validated["member_id"]
        # save_admin_bid aktualisiert ein bestehendes Gebot, deshalb bleibt das
        # Anlegen hier ein reines Anlegen und überschreibt nichts.
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
                items=validated["items"],
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
            BiddingRoundViewService.serialize_bid(bid, cache=cache),
            status=status.HTTP_201_CREATED,
        )


class BidEditView(BiddingRoundFeatureFlagMixin, APIView):
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(responses={200: BidSerializer}, request=BidAdminSerializer())
    def patch(self, request, round_id, bid_id):
        cache = {}
        bid = get_object_or_404(Bid, id=bid_id, round_id=round_id)
        serializer = BidAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        try:
            bid = BiddingRoundService.save_admin_bid(
                bidding_round=bid.round,
                member=bid.member,
                items=validated.get("items"),
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
            BiddingRoundViewService.serialize_bid(bid, cache=cache),
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={204: None})
    def delete(self, request, round_id, bid_id):
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
        if bid.round.average_bid_locked_at is not None:
            return Response(
                {
                    "error": _(
                        "Gebote können nach dem Fixieren des Durchschnittsgebots nicht mehr gelöscht werden."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        bid.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConfirmBidsView(BiddingRoundFeatureFlagMixin, APIView):
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(
        responses={200: RoundResultsResponseSerializer},
        request=ConfirmBidsSerializer(),
    )
    def post(self, request, round_id):
        cache = {}
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        serializer = ConfirmBidsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        BiddingRoundService.confirm_bids(
            bidding_round,
            bid_ids=serializer.validated_data.get("bid_ids"),
            cache=cache,
        )
        return Response(
            BiddingRoundStatsService.build_admin_evaluation(bidding_round, cache),
            status=status.HTTP_200_OK,
        )


class RoundLockAverageBidView(BiddingRoundFeatureFlagMixin, APIView):
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(responses={200: RoundSerializer}, request=LockAverageBidSerializer())
    def post(self, request, round_id):
        cache = {}
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
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(responses={200: RoundSerializer})
    def post(self, request, round_id):
        cache = {}
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


class MembersWithoutBidView(BiddingRoundFeatureFlagMixin, APIView):
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(responses={200: MemberOptionSerializer(many=True)})
    def get(self, request, round_id):
        bidding_round = get_object_or_404(BiddingRound, id=round_id)
        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        member_ids = (
            Subscription.objects.filter(
                period=bidding_round.growing_period,
                cancellation_ts__isnull=True,
            )
            .values_list("member_id", flat=True)
            .distinct()
        )
        members = (
            Member.objects.filter(id__in=member_ids)
            .exclude(id__in=bid_member_ids)
            .order_by("last_name", "first_name")
        )
        return Response(
            [
                {
                    "id": member.id,
                    "name": str(member),
                    "email": member.email,
                }
                for member in members
            ],
            status=status.HTTP_200_OK,
        )


class ExportCsvView(BiddingRoundFeatureFlagMixin, APIView):
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(responses={200: str})
    def get(self, request, round_id):
        bidding_round = get_object_or_404(BiddingRound, id=round_id)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="bidding_round_{bidding_round.id}.csv"'
        )
        response.write("\ufeff")
        response.write(BiddingRoundCsvExportService.build_csv(bidding_round, cache={}))
        return response


class CreateContractsView(BiddingRoundFeatureFlagMixin, APIView):
    permission_classes = [BiddingRoundManagePermission]

    @extend_schema(
        responses={200: CreateContractsResponseSerializer},
        request=CreateContractsSerializer(),
    )
    def post(self, request, round_id):
        cache = {}
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
                        "member_id": entry["member"].id,
                        "member_name": str(entry["member"]),
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
