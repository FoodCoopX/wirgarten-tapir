from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.generic_exports.models import CsvExport
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.generic_exports.serializers import (
    ExportSegmentSerializer,
    CsvExportModelSerializer,
)
from tapir.generic_exports.services.export_segment_manager import ExportSegmentManager
from tapir.wirgarten.constants import Permission


class CsvExportEditorView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Coop.MANAGE
    template_name = "generic_exports/csv_export_editor.html"


class GetExportSegmentsView(APIView):
    @extend_schema(
        responses={200: ExportSegmentSerializer(many=True)},
    )
    def get(self, request):
        if not request.user.has_perm(Permission.Coop.MANAGE):
            return Response(status=status.HTTP_403_FORBIDDEN)

        segment_datas = []
        for segment in ExportSegmentManager.registered_export_segments.values():
            segment_datas.append(
                {
                    "id": segment.id,
                    "display_name": segment.display_name,
                    "description": segment.description,
                    "columns": [
                        {
                            "id": column.id,
                            "display_name": column.display_name,
                            "description": column.description,
                        }
                        for column in segment.get_available_columns()
                    ],
                }
            )
        segment_datas.sort(key=lambda x: x["display_name"])

        return Response(
            ExportSegmentSerializer(segment_datas, many=True).data,
            status=status.HTTP_200_OK,
        )


class CsvExportViewSet(viewsets.ModelViewSet):
    queryset = CsvExport.objects.all().order_by("name")
    serializer_class = CsvExportModelSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
