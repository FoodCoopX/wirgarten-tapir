from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.generic_exports.models import CsvExport
from tapir.generic_exports.serializers import (
    ExportSegmentSerializer,
    CsvExportSerializer,
    CreateCsvExportSerializer,
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


class GetCsvExportsView(APIView):
    @extend_schema(
        responses={200: CsvExportSerializer(many=True)},
    )
    def get(self, request):
        if not request.user.has_perm(Permission.Coop.MANAGE):
            return Response(status=status.HTTP_403_FORBIDDEN)

        export_data = [
            self.build_export_data(export)
            for export in CsvExport.objects.order_by("name")
        ]

        return Response(
            CsvExportSerializer(export_data, many=True).data,
            status=status.HTTP_200_OK,
        )

    @classmethod
    def build_export_data(cls, export: CsvExport):
        return {
            "export_segment_id": export.export_segment_id,
            "export_segment_name": ExportSegmentManager.registered_export_segments[
                export.export_segment_id
            ].display_name,
            "name": export.name,
            "description": export.description,
            "separator": export.separator,
            "file_name": export.file_name,
            "email_recipients": export.email_recipients,
            "columns": cls.build_columns_data(export),
        }

    @staticmethod
    def build_columns_data(export: CsvExport):
        if (
            export.export_segment_id
            not in ExportSegmentManager.registered_export_segments.keys()
        ):
            return []

        export_segment = ExportSegmentManager.registered_export_segments[
            export.export_segment_id
        ]
        columns_by_id = {
            column.id: column for column in export_segment.get_available_columns()
        }

        return [
            {
                "id": column_id,
                "display_name": columns_by_id[column_id].display_name,
                "description": columns_by_id[column_id].display_name,
            }
            for column_id in export.column_ids
        ]


class CreateCsvExportView(APIView):
    @extend_schema(
        request=CreateCsvExportSerializer,
        responses={200: CsvExportSerializer()},
    )
    def post(self, request):
        if not request.user.has_perm(Permission.Coop.MANAGE):
            return Response(status=status.HTTP_403_FORBIDDEN)

        request_serializer = CreateCsvExportSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        export = CsvExport.objects.create(
            export_segment_id=request_serializer.validated_data["export_segment_id"],
            name=request_serializer.validated_data["name"],
            description=request_serializer.validated_data["description"],
            separator=request_serializer.validated_data["separator"],
            file_name=request_serializer.validated_data["file_name"],
            email_recipients=request_serializer.validated_data["email_recipients"],
            column_ids=request_serializer.validated_data["column_ids"],
        )

        return Response(
            CsvExportSerializer(
                GetCsvExportsView.build_export_data(export), many=True
            ).data,
            status=status.HTTP_200_OK,
        )
