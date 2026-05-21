from django.http import Http404

from tapir.generic_exports.services.pdf_export_template_manager import (
    PdfExportTemplateManager,
)
from tapir.generic_exports.services.pdf_templates.template_pick_list_by_pickup_location import (
    TemplatePickListByPickupLocation,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestPdfExportTemplateManager(TapirUnitTest):
    def test_getTemplates_default_buildsTemplateDataCorrectly(self):
        result = PdfExportTemplateManager.get_templates()

        data = result[TemplatePickListByPickupLocation.ID]
        self.assertEqual(TemplatePickListByPickupLocation.ID, data.id)
        self.assertEqual(TemplatePickListByPickupLocation.NAME, data.name)
        self.assertEqual(TemplatePickListByPickupLocation.DESCRIPTION, data.description)
        self.assertEqual(
            TemplatePickListByPickupLocation.create_exports, data.create_method
        )

    def test_createExportsFromTemplate_templateIdNotFound_raises404(self):
        with self.assertRaises(Http404) as error:
            PdfExportTemplateManager.create_exports_from_template("unknown")

        self.assertEqual(
            "Unknown template id \"unknown\", available IDs: ['pick_list_by_pickup_location']",
            str(error.exception),
        )
