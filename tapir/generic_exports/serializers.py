from rest_framework import serializers

from tapir.generic_exports.models import CsvExport, PdfExport


class ExportSegmentColumnSerializer(serializers.Serializer):
    id = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()


class ExportSegmentSerializer(serializers.Serializer):
    id = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    columns = ExportSegmentColumnSerializer(many=True)


class CsvExportModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CsvExport
        fields = "__all__"


class BuildCsvExportResponseSerializer(serializers.Serializer):
    file_name = serializers.CharField()
    file_as_string = serializers.CharField()


class PdfExportModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PdfExport
        fields = "__all__"
