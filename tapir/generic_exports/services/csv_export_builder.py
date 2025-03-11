import csv
import datetime
import io

from tapir.generic_exports.models import CsvExport
from tapir.generic_exports.services.export_segment_manager import (
    ExportSegmentManager,
    ExportSegment,
    ExportSegmentColumn,
)
from tapir.wirgarten.models import ExportedFile


class CsvExportBuilder:
    class CsvExportBuilderException(Exception):
        pass

    @classmethod
    def create_exported_file(
        cls, csv_export: CsvExport, reference_datetime: datetime.datetime
    ):
        return ExportedFile.objects.create(
            name=cls.build_file_name(csv_export.file_name, reference_datetime),
            type=ExportedFile.FileType.CSV,
            file=bytes(
                cls.build_csv_export_string(csv_export, reference_datetime), "utf-8"
            ),
        )

    @classmethod
    def build_csv_export_string(
        cls, csv_export: CsvExport, reference_datetime: datetime.datetime
    ):
        segment = ExportSegmentManager.registered_export_segments[
            csv_export.export_segment_id
        ]
        queryset = segment.get_queryset(reference_datetime)
        columns = [
            cls.get_column_by_id(segment, column_id)
            for column_id in csv_export.column_ids
        ]

        result = io.StringIO()
        writer = csv.writer(result, delimiter=csv_export.separator)

        # Header row
        writer.writerow([column.display_name for column in columns])

        for db_object in queryset:
            writer.writerow(
                [column.get_value(db_object, reference_datetime) for column in columns]
            )

        return result.getvalue()

    @classmethod
    def get_column_by_id(
        cls, segment: ExportSegment, column_id: str
    ) -> ExportSegmentColumn:
        for column in segment.get_available_columns():
            if column.id == column_id:
                return column

        raise cls.CsvExportBuilderException(
            f"Could not find column with id {column_id} in segment {segment.id}"
        )

    @classmethod
    def build_file_name(
        cls, base_name: str, reference_datetime: datetime.datetime
    ) -> str:
        name = base_name
        if base_name.endswith(".csv"):
            name = base_name[:-4]

        name += "." + reference_datetime.strftime("%Y.%m.%d %H.%M")
        name += ".csv"
        return name
