import datetime

import weasyprint
from django.template import engines
from django_weasyprint.utils import django_url_fetcher
from weasyprint import Document
from weasyprint.text.fonts import FontConfiguration

from tapir import settings
from tapir.generic_exports.models import PdfExport
from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.generic_exports.services.export_segment_manager import (
    ExportSegment,
    ExportSegmentManager,
)
from tapir.wirgarten.models import ExportedFile


class PdfExportBuilder:
    _WEASYPRINT_FONT_CONFIG = FontConfiguration()

    class PdfExportBuilderException(Exception):
        pass

    @classmethod
    def create_exported_files(
        cls, pdf_export: PdfExport, reference_datetime: datetime.datetime
    ):
        contexts = cls.build_contexts(pdf_export, reference_datetime)

        if pdf_export.generate_one_file_for_every_segment_entry:
            return [
                cls.create_single_file(
                    pdf_export,
                    reference_datetime,
                    context,
                )
                for context in contexts
            ]

        return [
            cls.create_single_file(
                pdf_export,
                reference_datetime,
                {"entries": contexts},
            )
        ]

    @classmethod
    def build_contexts(cls, pdf_export, reference_datetime):
        segment = ExportSegmentManager.get_segment_by_id(pdf_export.export_segment_id)
        used_column_ids = [
            column.id
            for column in segment.get_available_columns()
            if column.id in pdf_export.template
        ]

        return [
            cls.build_content_for_entry(
                entry, segment, reference_datetime, used_column_ids
            )
            for entry in segment.get_queryset(reference_datetime)
        ]

    @classmethod
    def create_single_file(cls, pdf_export, reference_datetime, context):
        return ExportedFile.objects.create(
            name=CsvExportBuilder.build_file_name(
                pdf_export.file_name, reference_datetime
            ),
            type=ExportedFile.FileType.PDF,
            file=bytes(
                cls.render_pdf(
                    pdf_export.template,
                    context,
                ).write_pdf(),
                "utf-8",
            ),
        )

    @classmethod
    def build_content_for_entry(
        cls,
        db_object,
        segment: ExportSegment,
        reference_datetime: datetime.datetime,
        used_column_ids,
    ):
        return {
            column.id: column.get_value(db_object, reference_datetime)
            for column in segment.get_available_columns()
            if column.id in used_column_ids
        }

    @classmethod
    def render_pdf(cls, template_as_string: str, context: dict) -> Document:
        document = weasyprint.HTML(
            string=cls.build_template_object(template_as_string).render(context),
            base_url=settings.WEASYPRINT_BASEURL,
            url_fetcher=django_url_fetcher,
        )
        return document.render(font_config=cls._WEASYPRINT_FONT_CONFIG)

    @classmethod
    def build_template_object(cls, template_string):
        """
        From https://stackoverflow.com/a/46756430

        Convert a string into a template object,
        using a given template engine or using the default backends
        from settings.TEMPLATES if no engine was specified.
        """
        # This function is based on django.template.loader.get_template,
        # but uses Engine.from_string instead of Engine.get_template.

        for engine in engines.all():
            return engine.from_string(template_string)
