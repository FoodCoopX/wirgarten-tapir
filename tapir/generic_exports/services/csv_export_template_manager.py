from django.http import Http404

from tapir.generic_exports.services.csv_templates.template_home_delivery_list import (
    TemplateHomeDeliveryList,
)
from tapir.generic_exports.services.csv_templates.template_joker_overview import (
    TemplateJokerOverview,
)
from tapir.generic_exports.services.csv_templates.template_member_list_geng import (
    TemplateMemberListGeng,
)
from tapir.generic_exports.services.csv_templates.template_payments_by_income_source import (
    TemplatePaymentsByIncomeSource,
)
from tapir.generic_exports.services.pdf_export_template_manager import TemplateData
from tapir.utils.services.tapir_cache import TapirCache


class CsvExportTemplateManager:
    @classmethod
    def get_templates(cls, cache: dict) -> dict[str, TemplateData]:
        template_list = [
            TemplateMemberListGeng,
            TemplateJokerOverview,
            TemplatePaymentsByIncomeSource,
        ]
        if any(
            pickup_location.is_home_delivery
            for pickup_location in TapirCache.get_all_pickup_locations(cache=cache)
        ):
            template_list.append(TemplateHomeDeliveryList)

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
        templates = cls.get_templates(cache=cache)
        if template_id not in templates:
            raise Http404(
                f'Unknown template id "{template_id}", available IDs: {list(templates.keys())}'
            )

        templates[template_id].create_method()
