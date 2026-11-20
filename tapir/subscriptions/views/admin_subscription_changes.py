from django.core.exceptions import ValidationError
from django.db import transaction
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
    AdminSizeChangeRequestSerializer,
    AdminSubscriptionAdditionRequestSerializer,
    OrderConfirmationResponseSerializer,
)
from tapir.subscriptions.services.admin_size_change_applier import (
    AdminSizeChangeApplier,
)
from tapir.subscriptions.services.admin_size_change_order_builder import (
    AdminSizeChangeOrderBuilder,
)
from tapir.subscriptions.services.admin_size_change_validator import (
    AdminSizeChangeValidator,
)
from tapir.subscriptions.services.admin_subscription_addition_applier import (
    AdminSubscriptionAdditionApplier,
)
from tapir.subscriptions.services.admin_subscription_addition_date_options_builder import (
    AdminSubscriptionAdditionDateOptionsBuilder,
)
from tapir.subscriptions.services.admin_subscription_addition_validator import (
    AdminSubscriptionAdditionValidator,
)
from tapir.subscriptions.services.admin_subscription_change_member_data_builder import (
    AdminSubscriptionChangeMemberDataBuilder,
)
from tapir.subscriptions.services.admin_size_change_date_options_builder import (
    AdminSizeChangeDateOptionsBuilder,
)
from tapir.subscriptions.types import (
    AdminSizeChangeRequest,
    AdminSubscriptionAdditionRequest,
    SubscriptionPrerequisitesInput,
)
from tapir.wirgarten.models import Member, Product, ProductType, Subscription
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
            "payment_rhythm": MemberPaymentRhythmService.get_rhythm_display_name(
                MemberPaymentRhythmService.get_member_payment_rhythm(
                    member=member, reference_date=get_today(cache=cache), cache=cache
                )
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


class AdminSizeChangeBaseApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @staticmethod
    def _build_size_change(request, cache: dict) -> AdminSizeChangeRequest:
        serializer = AdminSizeChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        member = get_object_or_404(Member, id=validated_data["member_id"])
        subscription = get_object_or_404(
            Subscription.objects.select_related("member", "product__type"),
            id=validated_data["subscription_id"],
        )
        new_product = get_object_or_404(
            Product.objects.select_related("type"),
            id=validated_data["new_product_id"],
        )
        change_date = validated_data["change_date"]

        return AdminSizeChangeRequest(
            member=member,
            subscription=subscription,
            new_product=new_product,
            change_date=change_date,
            order=AdminSizeChangeOrderBuilder.build_order(
                member=member,
                subscription=subscription,
                new_product=new_product,
                change_date=change_date,
                cache=cache,
            ),
            prerequisites=SubscriptionPrerequisitesInput(
                desired_pickup_location_id=validated_data.get("pickup_location_id"),
                iban=validated_data["iban"].strip(),
                account_owner=validated_data["account_owner"].strip(),
                sepa_mandate_confirmed=validated_data["sepa_mandate_confirmed"],
            ),
        )

    @staticmethod
    def _get_validation_error(
        size_change: AdminSizeChangeRequest, cache: dict
    ) -> str | None:
        try:
            AdminSizeChangeValidator.validate(size_change=size_change, cache=cache)
        except ValidationError as error:
            return " ".join(error.messages)
        return None


class AdminSizeChangeCheckApiView(AdminSizeChangeBaseApiView):
    @extend_schema(
        request=AdminSizeChangeRequestSerializer,
        responses={200: OrderConfirmationResponseSerializer},
    )
    def post(self, request):
        cache = {}
        error = self._get_validation_error(
            size_change=self._build_size_change(request=request, cache=cache),
            cache=cache,
        )
        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": error is None, "error": error}
            ).data
        )


class AdminSizeChangeApplyApiView(AdminSizeChangeBaseApiView):
    @extend_schema(
        request=AdminSizeChangeRequestSerializer,
        responses={200: OrderConfirmationResponseSerializer},
    )
    def post(self, request):
        cache = {}
        size_change = self._build_size_change(request=request, cache=cache)
        error = self._get_validation_error(size_change=size_change, cache=cache)
        if error is not None:
            return Response(
                OrderConfirmationResponseSerializer(
                    {"order_confirmed": False, "error": error}
                ).data
            )

        with transaction.atomic():
            AdminSizeChangeApplier.apply_change(
                size_change=size_change, actor=request.user, cache=cache
            )

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": None}
            ).data
        )


class AdminSubscriptionAdditionDateOptionsApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[OpenApiParameter(name="product_type_id", type=str)],
        responses={200: AdminSizeChangeDateOptionsSerializer},
    )
    def get(self, request):
        cache = {}
        product_type = get_object_or_404(
            ProductType, id=request.query_params.get("product_type_id")
        )

        return Response(
            AdminSizeChangeDateOptionsSerializer(
                AdminSubscriptionAdditionDateOptionsBuilder.build(
                    product_type=product_type, cache=cache
                )
            ).data
        )


class AdminSubscriptionAdditionBaseApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @staticmethod
    def _build_addition(request) -> AdminSubscriptionAdditionRequest:
        serializer = AdminSubscriptionAdditionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        member = get_object_or_404(Member, id=validated_data["member_id"])
        product = get_object_or_404(
            Product.objects.select_related("type"), id=validated_data["product_id"]
        )
        quantity = validated_data["quantity"]
        start_date = validated_data["start_date"]

        return AdminSubscriptionAdditionRequest(
            member=member,
            product=product,
            quantity=quantity,
            start_date=start_date,
            prerequisites=SubscriptionPrerequisitesInput(
                desired_pickup_location_id=validated_data.get("pickup_location_id"),
                iban=validated_data["iban"].strip(),
                account_owner=validated_data["account_owner"].strip(),
                sepa_mandate_confirmed=validated_data["sepa_mandate_confirmed"],
            ),
        )

    @staticmethod
    def _get_validation_error(
        addition: AdminSubscriptionAdditionRequest, cache: dict
    ) -> str | None:
        try:
            AdminSubscriptionAdditionValidator.validate(addition=addition, cache=cache)
        except ValidationError as error:
            return " ".join(error.messages)
        return None


class AdminSubscriptionAdditionCheckApiView(AdminSubscriptionAdditionBaseApiView):
    @extend_schema(
        request=AdminSubscriptionAdditionRequestSerializer,
        responses={200: OrderConfirmationResponseSerializer},
    )
    def post(self, request):
        cache = {}
        error = self._get_validation_error(
            addition=self._build_addition(request=request), cache=cache
        )
        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": error is None, "error": error}
            ).data
        )


class AdminSubscriptionAdditionApplyApiView(AdminSubscriptionAdditionBaseApiView):
    @extend_schema(
        request=AdminSubscriptionAdditionRequestSerializer,
        responses={200: OrderConfirmationResponseSerializer},
    )
    def post(self, request):
        cache = {}
        addition = self._build_addition(request=request)
        error = self._get_validation_error(addition=addition, cache=cache)
        if error is not None:
            return Response(
                OrderConfirmationResponseSerializer(
                    {"order_confirmed": False, "error": error}
                ).data
            )

        with transaction.atomic():
            AdminSubscriptionAdditionApplier.apply_addition(
                addition=addition, actor=request.user, cache=cache
            )

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": None}
            ).data
        )
