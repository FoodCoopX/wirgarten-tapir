import datetime

from tapir.generic_exports.exceptions import TemplateAlreadyExistsException
from tapir.generic_exports.models import AutomatedExportCycle, CsvExport
from tapir.generic_exports.services.csv_templates.template_home_delivery_list import (
    TemplateHomeDeliveryList,
)
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider
from tapir.generic_exports.services.member_segment_provider import MemberSegmentProvider
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestTemplateHomeDeliveryList(TapirIntegrationTest):
    def test_createExports_default_createsCorrectExport(self):
        TemplateHomeDeliveryList.create_exports()

        export = CsvExport.objects.get()
        self.assertEqual(
            MemberSegmentProvider.SEGMENT_ID_WITH_HOME_DELIVERY_THIS_WEEK,
            export.export_segment_id,
        )
        self.assertEqual(AutomatedExportCycle.WEEKLY, export.automated_export_cycle)
        self.assertEqual(1, export.automated_export_day)
        self.assertEqual(datetime.time(hour=6), export.automated_export_hour)
        self.assertEqual(
            [
                MemberColumnProvider.COLUMN_ID_DELIVERY_DATE,
                MemberColumnProvider.COLUMN_ID_MEMBER_NUMBER,
                MemberColumnProvider.COLUMN_ID_LAST_NAME,
                MemberColumnProvider.COLUMN_ID_FIRST_NAME,
                MemberColumnProvider.COLUMN_ID_DELIVERY_STREET,
                MemberColumnProvider.COLUMN_ID_DELIVERY_STREET_2,
                MemberColumnProvider.COLUMN_ID_DELIVERY_POSTCODE,
                MemberColumnProvider.COLUMN_ID_DELIVERY_CITY,
                MemberColumnProvider.COLUMN_ID_PHONE_NUMBER,
                MemberColumnProvider.COLUMN_ID_EMAIL_ADDRESS,
            ],
            export.column_ids,
        )

    def test_createExports_exportAlreadyExists_raisesException(self):
        TemplateHomeDeliveryList.create_exports()

        with self.assertRaises(TemplateAlreadyExistsException):
            TemplateHomeDeliveryList.create_exports()
