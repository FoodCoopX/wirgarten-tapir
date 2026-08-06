from tapir.configuration.models import TapirParameter
from tapir.generic_exports.models import PdfExport, AutomatedExportCycle
from tapir.generic_exports.services.pdf_templates.template_basket_totals_by_route import (
    TemplateBasketTotalsByRoute,
)
from tapir.pickup_locations.services.pickup_location_segment_provider import (
    PickupLocationSegmentProvider,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestTemplateBasketTotalsByRoute(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_createExports_default_createsCorrectExport(self):
        TapirParameter.objects.filter(key=ParameterKeys.SITE_ADMIN_EMAIL).update(
            value="admin@example.com"
        )

        TemplateBasketTotalsByRoute.create_exports()

        export = PdfExport.objects.get()

        self.assertEqual(TemplateBasketTotalsByRoute.NAME, export.name)
        self.assertEqual(
            PickupLocationSegmentProvider.SEGMENT_ID_ALL_LOCATION_ROUTES,
            export.export_segment_id,
        )
        self.assertFalse(export.generate_one_file_for_every_segment_entry)
        self.assertEqual(
            AutomatedExportCycle.AFTER_PICKUP_LOCATION_CHANGE_DEADLINE,
            export.automated_export_cycle,
        )
        self.assertEqual(["admin@example.com"], export.email_recipients)
        self.assertIn("route_basket_totals", export.template)
        self.assertIn("route_name", export.template)
