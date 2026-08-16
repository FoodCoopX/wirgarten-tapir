from django.http import Http404

from tapir.core.config import THEME_TEST
from tapir.generic_exports.services.pdf_export_template_manager import (
    PdfExportTemplateManager,
)
from tapir.generic_exports.services.pdf_templates.template_basket_totals_by_route import (
    TemplateBasketTotalsByRoute,
)
from tapir.generic_exports.services.pdf_templates.template_pick_list_by_pickup_location import (
    TemplatePickListByPickupLocation,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestPdfExportTemplateManager(TapirUnitTest):
    def test_getTemplates_default_buildsTemplateDataCorrectly(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.ORGANISATION_THEME, value=THEME_TEST
        )

        result = PdfExportTemplateManager.get_templates(cache)

        data = result[TemplatePickListByPickupLocation.ID]
        self.assertEqual(TemplatePickListByPickupLocation.ID, data.id)
        self.assertEqual(TemplatePickListByPickupLocation.NAME, data.name)
        self.assertEqual(TemplatePickListByPickupLocation.DESCRIPTION, data.description)
        self.assertEqual(
            TemplatePickListByPickupLocation.create_exports, data.create_method
        )
        self.assertIn(TemplateBasketTotalsByRoute.ID, result)

    def test_createExportsFromTemplate_templateIdNotFound_raises404(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.ORGANISATION_THEME, value=THEME_TEST
        )

        with self.assertRaises(Http404) as error:
            PdfExportTemplateManager.create_exports_from_template("unknown", cache)

        self.assertEqual(
            "Unknown template id \"unknown\", available IDs: ['pick_list_by_pickup_location', 'location_routes', 'basket_totals_by_route']",
            str(error.exception),
        )
