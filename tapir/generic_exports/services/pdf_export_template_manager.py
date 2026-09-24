from dataclasses import dataclass
from typing import Callable

from django.http import Http404

from tapir.configuration.parameter import get_parameter_value
from tapir.core.config import THEME_BIOTOP
from tapir.generic_exports.services.pdf_templates.template_basket_totals_by_route import (
    TemplateBasketTotalsByRoute,
)
from tapir.generic_exports.services.pdf_templates.template_basket_totals_by_route_biotop import (
    TemplateBasketTotalsByRouteBiotop,
)
from tapir.generic_exports.services.pdf_templates.template_location_routes import (
    TemplateLocationRoutes,
)
from tapir.generic_exports.services.pdf_templates.template_location_routes_biotop import (
    TemplateLocationRoutesBiotop,
)
from tapir.generic_exports.services.pdf_templates.template_pick_list_by_pickup_location import (
    TemplatePickListByPickupLocation,
)
from tapir.wirgarten.parameter_keys import ParameterKeys


@dataclass
class TemplateData:
    id: str
    name: str
    description: str
    create_method: Callable[[], None]


class PdfExportTemplateManager:
    @classmethod
    def get_templates(cls, cache: dict) -> dict[str, TemplateData]:
        template_list = [TemplatePickListByPickupLocation]
        if (
            get_parameter_value(key=ParameterKeys.ORGANISATION_THEME, cache=cache)
            == THEME_BIOTOP
        ):
            template_list.append(TemplateLocationRoutesBiotop)
            template_list.append(TemplateBasketTotalsByRouteBiotop)
        else:
            template_list.append(TemplateLocationRoutes)
            template_list.append(TemplateBasketTotalsByRoute)

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
    def create_exports_from_template(cls, template_id: str, cache: dict):
        templates = cls.get_templates(cache)
        if template_id not in templates:
            raise Http404(
                f'Unknown template id "{template_id}", available IDs: {list(templates.keys())}'
            )

        templates[template_id].create_method()
