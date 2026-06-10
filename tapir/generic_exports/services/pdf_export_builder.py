import datetime

import typst
import weasyprint
from django.template import engines

from tapir.core import json
from tapir.generic_exports.models import PdfExport
from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.generic_exports.services.export_segment_manager import (
    ExportSegment,
    ExportSegmentManager,
)
from tapir.wirgarten.models import ExportedFile
from tapir.wirgarten.utils import get_today


class PdfExportBuilder:
    class PdfExportBuilderException(Exception):
        pass

    @classmethod
    def create_exported_files(
        cls, pdf_export: PdfExport, reference_datetime: datetime.datetime
    ):
        cache = {}
        contexts, use_typst = cls.build_contexts(
            pdf_export, reference_datetime, cache=cache
        )

        if pdf_export.generate_one_file_for_every_segment_entry:
            return [
                cls.create_single_file(
                    pdf_export,
                    reference_datetime,
                    context | {"today": get_today(cache=cache)},
                    use_typst,
                )
                for context in contexts
            ]

        return [
            cls.create_single_file(
                pdf_export,
                reference_datetime,
                {"entries": contexts, "today": get_today(cache=cache)},
                use_typst,
            )
        ]

    @classmethod
    def build_contexts(cls, pdf_export, reference_datetime, cache: dict):
        segment = ExportSegmentManager.get_segment_by_id(pdf_export.export_segment_id)
        used_column_ids = [
            column.id
            for column in segment.get_available_columns()
            if column.id in pdf_export.template
        ]

        return (
            [
                cls.build_context_for_entry(
                    entry, segment, reference_datetime, used_column_ids, cache=cache
                )
                for entry in segment.get_queryset(reference_datetime)
            ],
            segment.use_typst,
        )

    @classmethod
    def create_single_file(cls, pdf_export, reference_datetime, context, use_typst):
        rendered_file_name = cls.render_template_string(pdf_export.file_name, context)

        if use_typst:
            pdf_file = cls.render_pdf_typst(
                pdf_export.template, context, reference_datetime
            )
        else:
            pdf_file = cls.render_pdf_weasyprint(
                pdf_export.template,
                context,
            )

        exported_file = ExportedFile.objects.create(
            name=CsvExportBuilder.build_file_name(
                rendered_file_name, reference_datetime, "pdf"
            ),
            type=ExportedFile.FileType.PDF,
            file=pdf_file,
        )
        return exported_file

    @classmethod
    def build_context_for_entry(
        cls,
        db_object,
        segment: ExportSegment,
        reference_datetime: datetime.datetime,
        used_column_ids,
        cache: dict,
    ):
        return {
            column.id: column.get_value(db_object, reference_datetime, cache)
            for column in segment.get_available_columns()
            if column.id in used_column_ids
        }

    @classmethod
    def render_pdf_typst(
        cls,
        template_as_string: str,
        context: dict,
        reference_datetime: datetime.datetime,
    ) -> bytes:
        sys_inputs = {}
        if "entries" in context:
            sys_inputs["entries"] = json.dumps_with_encoder(context["entries"])
        else:
            del context["today"]
            sys_inputs["entry"] = json.dumps_with_encoder(context)
        # print(sys_inputs)  # see the json used for the rendering

        return typst.compile(
            str.encode(template_as_string),
            sys_inputs=sys_inputs,
            format="pdf",
            timestamp=int(reference_datetime.timestamp()),
        )

    @classmethod
    def render_pdf_weasyprint(cls, template_as_string: str, context: dict) -> bytes:
        rendered_template = cls.render_template_string(template_as_string, context)
        document = weasyprint.HTML(
            string=rendered_template,
        )
        return document.render().write_pdf()

    @classmethod
    def render_template_string(cls, template_string: str, context: dict):
        """
        From https://stackoverflow.com/a/46756430

        Create a string from a template using the default backends
        from settings.TEMPLATES.
        """
        # This function is based on django.template.loader.get_template,
        # but uses Engine.from_string instead of Engine.get_template.

        for engine in engines.all():
            return engine.from_string(template_string).render(context)

        # no engine found: return template_string as-is
        return template_string
