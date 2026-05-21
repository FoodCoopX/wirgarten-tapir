import datetime

from tapir.generic_exports.models import PdfExport, AutomatedExportCycle
from tapir.generic_exports.services.pdf_templates.template_pick_list_by_pickup_location import (
    TemplatePickListByPickupLocation,
)
from tapir.pickup_locations.services.pickup_location_segment_provider import (
    PickupLocationSegmentProvider,
)
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestTemplatePickListByPickupLocation(TapirIntegrationTest):
    def test_createTemplate_default_createsOneExportPerPickupLocation(self):
        PickupLocationFactory.create(name="PL1")
        PickupLocationFactory.create(name="PL2")

        TemplatePickListByPickupLocation.create_exports()

        self.assertEqual(2, PdfExport.objects.count())

        export_1 = PdfExport.objects.get(name="Kommissionierungsliste PL1")
        self.assertEqual(
            PickupLocationSegmentProvider.SEGMENT_ID_ALL_PICKUP_LOCATIONS,
            export_1.export_segment_id,
        )
        self.assertEqual("Kommissionierungsliste PL1.pdf", export_1.file_name)
        self.assertEqual(AutomatedExportCycle.WEEKLY, export_1.automated_export_cycle)
        self.assertEqual(1, export_1.automated_export_day)
        self.assertEqual(datetime.time(hour=7), export_1.automated_export_hour)
        self.assertFalse(export_1.generate_one_file_for_every_segment_entry)
        self.assertIn("PL1", export_1.template)
        self.assertNotIn("PICKUP_LOCATION_NAME", export_1.template)

        export_2 = PdfExport.objects.get(name="Kommissionierungsliste PL2")
        self.assertEqual(
            PickupLocationSegmentProvider.SEGMENT_ID_ALL_PICKUP_LOCATIONS,
            export_2.export_segment_id,
        )
        self.assertEqual("Kommissionierungsliste PL2.pdf", export_2.file_name)
        self.assertEqual(AutomatedExportCycle.WEEKLY, export_2.automated_export_cycle)
        self.assertEqual(1, export_2.automated_export_day)
        self.assertEqual(datetime.time(hour=7), export_2.automated_export_hour)
        self.assertFalse(export_2.generate_one_file_for_every_segment_entry)
        self.assertIn("PL2", export_2.template)
        self.assertNotIn("PICKUP_LOCATION_NAME", export_2.template)
