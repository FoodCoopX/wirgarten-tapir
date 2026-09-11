from tapir.deliveries.services.joker_column_provider import JokerColumnProvider
from tapir.deliveries.services.joker_segment_provider import JokerSegmentProvider
from tapir.generic_exports.models import CsvExport
from tapir.generic_exports.services.csv_templates.template_joker_overview import (
    TemplateJokerOverview,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestTemplateJokerOverview(TapirIntegrationTest):
    def test_createExports_default_createsCorrectExport(self):
        TemplateJokerOverview.create_exports()

        export = CsvExport.objects.get()
        self.assertEqual(
            JokerSegmentProvider.SEGMENT_ID_JOKER_THIS_GROWING_PERIOD,
            export.export_segment_id,
        )
        self.assertEqual(
            [
                JokerColumnProvider.COLUMN_ID_MEMBER_NUMBER,
                JokerColumnProvider.COLUMN_ID_MEMBER_LAST_NAME,
                JokerColumnProvider.COLUMN_ID_PICKUP_LOCATION,
                JokerColumnProvider.COLUMN_ID_PRODUCT_TYPES,
                JokerColumnProvider.COLUMN_ID_PRODUCTS,
                JokerColumnProvider.COLUMN_ID_CALENDAR_WEEK,
            ],
            export.column_ids,
        )
