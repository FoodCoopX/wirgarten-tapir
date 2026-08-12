from django.http import Http404

from tapir.generic_exports.services.csv_templates.template_member_list_geng import (
    TemplateMemberListGeng,
)
from tapir.generic_exports.services.pdf_export_template_manager import TemplateData


class CsvExportTemplateManager:
    @classmethod
    def get_templates(cls) -> dict[str, TemplateData]:
        template_list = [TemplateMemberListGeng]

        return {
            template.ID: TemplateData(
                id=template.ID,
                name=template.NAME,
                description=template.DESCRIPTION,
                create_method=template.create_exports,
            )
            for template in template_list
        }

    @classmethod
    def create_exports_from_template(cls, template_id: str):
        templates = cls.get_templates()
        if template_id not in templates:
            raise Http404(
                f'Unknown template id "{template_id}", available IDs: {list(templates.keys())}'
            )

        templates[template_id].create_method()
