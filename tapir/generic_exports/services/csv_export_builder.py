import csv
import datetime
import io
import locale

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
            name=cls.build_file_name(csv_export.file_name, reference_datetime, "csv"),
            type=ExportedFile.FileType.CSV,
            file=bytes(
                cls.build_csv_export_string(csv_export, reference_datetime), "utf-8"
            ),
        )

    @classmethod
    def build_csv_export_string(
        cls, csv_export: CsvExport, reference_datetime: datetime.datetime
    ):
        segment = ExportSegmentManager.get_segment_by_id(csv_export.export_segment_id)
        queryset = segment.get_queryset(reference_datetime)
        columns = [
            cls.get_column_by_id(segment, column_id)
            for column_id in csv_export.column_ids
        ]

        result = io.StringIO()
        writer = csv.writer(result, delimiter=csv_export.separator)

        # Header row
        writer.writerow([name for name in csv_export.custom_column_names])

        previous_locale = locale.getlocale()
        locale.setlocale(locale.LC_NUMERIC, csv_export.locale)
        cache = {}
        for db_object in queryset:
            writer.writerow(
                [
                    column.get_value(db_object, reference_datetime, cache)
                    for column in columns
                ]
            )
        locale.setlocale(locale.LC_NUMERIC, previous_locale)

        return result.getvalue()

    @classmethod
    def get_column_by_id(
        cls, segment: ExportSegment, column_id: str
    ) -> ExportSegmentColumn:
        if column_id == "":
            return ExportSegmentColumn(
                id="",
                get_value=lambda _, __, ___: "",
                display_name="Leere Spalte",
                description="",
            )

        for column in segment.get_available_columns():
            if column.id == column_id:
                return column

        raise cls.CsvExportBuilderException(
            f"Could not find column with id {column_id} in segment {segment.id}"
        )

    @classmethod
    def build_file_name(
        cls, base_name: str, reference_datetime: datetime.datetime, extension: str
    ) -> str:
        if not extension.startswith("."):
            extension = "." + extension

        name = base_name
        if base_name.endswith(extension):
            name = base_name[: -len(extension)]

        name += "." + reference_datetime.strftime("%Y.%m.%d %H.%M")
        name += extension
        return name
