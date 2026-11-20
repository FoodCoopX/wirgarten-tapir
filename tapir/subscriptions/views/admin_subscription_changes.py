from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.coop.services.member_search_service import MemberSearchService
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.subscriptions.serializers import (
    AdminSubscriptionChangeMemberDataSerializer,
    AdminSubscriptionChangeMemberSummarySerializer,
    AdminSizeChangeDateOptionsSerializer,
)
from tapir.subscriptions.services.admin_subscription_change_member_data_builder import (
    AdminSubscriptionChangeMemberDataBuilder,
)
from tapir.subscriptions.services.admin_size_change_date_options_builder import (
    AdminSizeChangeDateOptionsBuilder,
)
from tapir.wirgarten.models import Member, Subscription
from tapir.wirgarten.utils import get_today


class AdminSubscriptionChangeMemberSearchApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
    MAX_RESULTS = 20

    @extend_schema(
        parameters=[OpenApiParameter(name="search", type=str)],
        responses={200: AdminSubscriptionChangeMemberSummarySerializer(many=True)},
    )
    def get(self, request):
        cache = {}
        search = request.query_params.get("search", "")
        if not search.strip():
            return Response([])

        members = MemberSearchService.filter_queryset(
            queryset=Member.objects.order_by("member_no", "last_name", "first_name"),
            search_value=search,
            cache=cache,
        )[: self.MAX_RESULTS]

        return Response(
            AdminSubscriptionChangeMemberSummarySerializer(
                [
                    AdminSubscriptionChangeMemberDataBuilder.build_member_summary(
                        member=member, cache=cache
                    )
                    for member in members
                ],
                many=True,
            ).data
        )


class AdminSubscriptionChangeMemberDataApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[OpenApiParameter(name="member_id", type=str)],
        responses={200: AdminSubscriptionChangeMemberDataSerializer},
    )
    def get(self, request):
        cache = {}
        member = get_object_or_404(Member, id=request.query_params.get("member_id"))

        data = {
            "member": AdminSubscriptionChangeMemberDataBuilder.build_member_summary(
                member=member, cache=cache
            ),
            "subscription_units": AdminSubscriptionChangeMemberDataBuilder.build_subscription_units(
                member=member, cache=cache
            ),
            "prerequisites": AdminSubscriptionChangeMemberDataBuilder.build_prerequisites_status(
                member=member, cache=cache
            ),
            "payment_rhythm": MemberPaymentRhythmService.get_member_payment_rhythm(
                member=member, reference_date=get_today(cache=cache), cache=cache
            ),
        }
        return Response(AdminSubscriptionChangeMemberDataSerializer(data).data)


class AdminSizeChangeDateOptionsApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[OpenApiParameter(name="subscription_id", type=str)],
        responses={200: AdminSizeChangeDateOptionsSerializer},
    )
    def get(self, request):
        cache = {}
        subscription = get_object_or_404(
            Subscription.objects.select_related("member", "product__type"),
            id=request.query_params.get("subscription_id"),
        )

        return Response(
            AdminSizeChangeDateOptionsSerializer(
                AdminSizeChangeDateOptionsBuilder.build(
                    subscription=subscription, cache=cache
                )
            ).data
        )
