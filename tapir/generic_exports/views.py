import datetime

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.generic_exports.models import CsvExport, PdfExport
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.generic_exports.serializers import (
    ExportSegmentSerializer,
    CsvExportModelSerializer,
    BuildCsvExportResponseSerializer,
    PdfExportModelSerializer,
)
from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.generic_exports.services.export_segment_manager import ExportSegmentManager
from tapir.generic_exports.services.pdf_export_builder import PdfExportBuilder
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


class BuildCsvExportView(APIView):
    @extend_schema(
        responses={200: BuildCsvExportResponseSerializer()},
        parameters=[
            OpenApiParameter(name="csv_export_id", type=str),
            OpenApiParameter(name="reference_datetime", type=datetime.datetime),
        ],
    )
    def get(self, request):
        if not request.user.has_perm(Permission.Coop.MANAGE):
            return Response(status=status.HTTP_403_FORBIDDEN)

        csv_export = get_object_or_404(
            CsvExport, id=request.query_params.get("csv_export_id")
        )
        reference_datetime = datetime.datetime.fromisoformat(
            request.query_params.get("reference_datetime")
        )

        exported_file = CsvExportBuilder.create_exported_file(
            csv_export, reference_datetime
        )

        return Response(
            BuildCsvExportResponseSerializer(
                {
                    "file_name": exported_file.name,
                    "file_as_string": exported_file.file.decode("utf-8"),
                }
            ).data,
            status=status.HTTP_200_OK,
        )


class PdfExportEditorView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Coop.MANAGE
    template_name = "generic_exports/pdf_export_editor.html"


class PdfExportViewSet(viewsets.ModelViewSet):
    queryset = PdfExport.objects.all().order_by("name")
    serializer_class = PdfExportModelSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]


class BuildPdfExportView(APIView):
    @extend_schema(
        responses={200: str},
        parameters=[
            OpenApiParameter(name="pdf_export_id", type=str),
            OpenApiParameter(name="reference_datetime", type=datetime.datetime),
        ],
    )
    def get(self, request):
        if not request.user.has_perm(Permission.Coop.MANAGE):
            return Response(status=status.HTTP_403_FORBIDDEN)

        pdf_export = get_object_or_404(
            PdfExport, id=request.query_params.get("pdf_export_id")
        )
        reference_datetime = datetime.datetime.fromisoformat(
            request.query_params.get("reference_datetime")
        )

        exported_files = PdfExportBuilder.create_exported_files(
            pdf_export, reference_datetime
        )

        return Response(
            reverse("wirgarten:exported_files_download", args=[exported_files[0].id]),
            status=status.HTTP_200_OK,
        )
