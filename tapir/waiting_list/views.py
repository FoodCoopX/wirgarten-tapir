from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import permissions
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.views import APIView

from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.waiting_list.serializers import WaitingListEntrySerializer
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import WaitingListEntry


class WaitingListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "waiting_list/list.html"
    permission_required = Permission.Coop.MANAGE


class WaitingListApiView(APIView):
    serializer_class = WaitingListEntrySerializer(many=True)
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
    pagination_class = LimitOffsetPagination

    @extend_schema(
        responses={200: WaitingListEntrySerializer(many=True)},
        parameters=[
            OpenApiParameter(name="limit", type=int, required=True),
            OpenApiParameter(name="offset", type=int, required=True),
        ],
    )
    def get(self, request):
        pagination = self.pagination_class()
        entries = WaitingListEntry.objects.order_by("created_at").prefetch_related(
            "product_wishes", "pickup_location_wishes"
        )
        entries = pagination.paginate_queryset(entries, request)
