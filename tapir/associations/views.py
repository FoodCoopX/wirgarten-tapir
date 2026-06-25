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
)
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.wirgarten.utils import check_permission_or_self


# Create your views here.
class AssociationMembershipConfigView(TemplateView):
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
