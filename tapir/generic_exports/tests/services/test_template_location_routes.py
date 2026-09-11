from tapir.generic_exports.models import PdfExport
from tapir.generic_exports.services.pdf_templates.template_location_routes import (
    TemplateLocationRoutes,
)
from tapir.pickup_locations.services.pickup_location_segment_provider import (
    PickupLocationSegmentProvider,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestTemplateLocationRoutes(TapirIntegrationTest):
    def test_createExports_default_createsCorrectExport(self):
        TemplateLocationRoutes.create_exports()

        export = PdfExport.objects.get()

        self.assertEqual(
            PickupLocationSegmentProvider.SEGMENT_ID_ALL_LOCATION_ROUTES,
            export.export_segment_id,
        )
        self.assertFalse(export.generate_one_file_for_every_segment_entry)
