from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.associations.models import (
    AssociationMembershipType,
    AssociationMembershipTypePrice,
    AssociationMembership,
)
from tapir.associations.serializers import (
    AssociationMembershipTypeSerializer,
    AssociationMembershipTypePriceSerializer,
    AssociationMembershipSerializer,
    AdminSetAssociationMembershipRequestSerializer,
)
from tapir.associations.services.association_membership_change_handler import (
    AssociationMembershipChangeHandler,
)
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.subscriptions.serializers import OrderConfirmationResponseSerializer
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import check_permission_or_self


class AssociationMembershipConfigView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Coop.MANAGE
    template_name = "associations/association_membership_config_view.html"


class AssociationMembershipTypeViewSet(viewsets.ModelViewSet):
    queryset = AssociationMembershipType.objects.all()
    serializer_class = AssociationMembershipTypeSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["cache"] = context.get("cache", {})
        return context


class AssociationMembershipTypePriceViewSet(viewsets.ModelViewSet):
    queryset = AssociationMembershipTypePrice.objects.all()
    serializer_class = AssociationMembershipTypePriceSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["cache"] = context.get("cache", {})
        return context


class MemberAssociationMembershipDetails(APIView):
    permission_classes = []

    @extend_schema(
        parameters=[OpenApiParameter(name="member_id", type=str)],
        responses={200: AssociationMembershipSerializer(many=True)},
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)

        return Response(
            AssociationMembershipSerializer(
                AssociationMembership.objects.filter(member_id=member_id).order_by(
                    "start_date"
                ),
                many=True,
                context={"cache": {}},
            ).data
        )


class AdminSetAssociationMembership(APIView):
    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=AdminSetAssociationMembershipRequestSerializer,
    )
    def post(self, request):
        serializer = AdminSetAssociationMembershipRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member = get_object_or_404(Member, id=serializer.validated_data["member_id"])
        membership_type = get_object_or_404(
            AssociationMembershipType,
            id=serializer.validated_data["membership_type_id"],
        )
        start_date = serializer.validated_data["start_date"]

        with transaction.atomic():
            AssociationMembershipChangeHandler.start_membership(
                member=member,
                association_membership_type=membership_type,
                start_date=start_date,
                actor=request.user,
            )

        return Response(OrderConfirmationResponseSerializer({"order_confirmed": True}))
