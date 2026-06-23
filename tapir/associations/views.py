from django.views.generic import TemplateView
from rest_framework import viewsets, permissions

from tapir.associations.models import AssociationMembershipType
from tapir.associations.serializers import AssociationMembershipTypeSerializer
from tapir.generic_exports.permissions import HasCoopManagePermission


# Create your views here.
class AssociationMembershipConfigView(TemplateView):
    template_name = "associations/association_membership_config_view.html"


class AssociationMembershipTypeViewSet(viewsets.ModelViewSet):
    queryset = AssociationMembershipType.objects.all()
    serializer_class = AssociationMembershipTypeSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
