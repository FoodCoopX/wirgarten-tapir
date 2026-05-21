from dataclasses import dataclass
from typing import Callable

from django.http import Http404

from tapir.generic_exports.services.pdf_templates.template_pick_list_by_pickup_location import (
    TemplatePickListByPickupLocation,
)


@dataclass
class TemplateData:
    id: str
    name: str
    description: str
    create_method: Callable[[], None]


class PdfExportTemplateManager:
    @classmethod
    def get_templates(cls) -> dict[str, TemplateData]:
        return {
            template.ID: TemplateData(
                id=template.ID,
                name=template.NAME,
                description=template.DESCRIPTION,
                create_method=template.create_exports,
            )
            for template in [TemplatePickListByPickupLocation]
        }

    @classmethod
    def create_exports_from_template(cls, template_id: str):
        templates = cls.get_templates()
        if template_id not in templates:
            raise Http404(
                f'Unknown template id "{template_id}", available IDs: {list(templates.keys())}'
            )

        templates[template_id].create_method()
