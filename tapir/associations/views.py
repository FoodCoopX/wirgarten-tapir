from django.views.generic import TemplateView
from rest_framework import viewsets, permissions

from tapir.associations.models import (
    AssociationMembershipType,
    AssociationMembershipTypePrice,
)
from tapir.associations.serializers import (
    AssociationMembershipTypeSerializer,
    AssociationMembershipTypePriceSerializer,
)
from tapir.generic_exports.permissions import HasCoopManagePermission


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
