from rest_framework import serializers

from tapir.generic_exports.models import CsvExport
from tapir.generic_exports.services.export_segment_manager import ExportSegmentManager


class ExportSegmentColumnSerializer(serializers.Serializer):
    id = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()


class ExportSegmentSerializer(serializers.Serializer):
    id = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    columns = ExportSegmentColumnSerializer(many=True)


class CsvExportSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    export_segment_id = serializers.CharField()
    export_segment_name = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    separator = serializers.CharField()
    file_name = serializers.CharField()
    columns = ExportSegmentColumnSerializer(many=True)
    email_recipients = serializers.ListField(child=serializers.EmailField())


class CsvExportModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CsvExport
        fields = "__all__"


class CreateCsvExportSerializer(serializers.Serializer):
    export_segment_id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    separator = serializers.CharField()
    file_name = serializers.CharField()
    columns_ids = serializers.ListField(child=serializers.CharField())
    email_recipients = serializers.ListField(child=serializers.EmailField())

    @staticmethod
    def validate(data):
        if (
            data["export_segment_id"]
            not in ExportSegmentManager.registered_export_segments.keys()
        ):
            raise serializers.ValidationError(
                f"Invalid export segment ID {data['export_segment_id']}"
            )

        segment = ExportSegmentManager.registered_export_segments[
            data["export_segment_id"]
        ]
        column_ids = [column.id for column in segment.get_available_columns()]
        for column_id in data["columns_ids"]:
            if column_id not in column_ids:
                raise serializers.ValidationError(f"Invalid column ID: {column_id}")

        return data
