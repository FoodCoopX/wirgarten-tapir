from unittest.mock import patch

from django.http import Http404

from tapir.generic_exports.services.csv_export_template_manager import (
    CsvExportTemplateManager,
)
from tapir.generic_exports.services.csv_templates.template_home_delivery_list import (
    TemplateHomeDeliveryList,
)
from tapir.generic_exports.services.csv_templates.template_joker_overview import (
    TemplateJokerOverview,
)
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestCsvExportTemplateManager(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.enterContext(
            patch(
                "tapir.generic_exports.services.csv_export_template_manager.legal_status_is_association",
                return_value=False,
            )
        )

    @staticmethod
    def _build_cache(pickup_locations: list[PickupLocation]) -> dict:
        return {
            "pickup_location_by_id": {
                pickup_location.id: pickup_location
                for pickup_location in pickup_locations
            }
        }

    def test_getTemplates_default_buildsTemplateDataCorrectly(self):
        result = CsvExportTemplateManager.get_templates(cache=self._build_cache([]))

        data = result[TemplateJokerOverview.ID]
        self.assertEqual(TemplateJokerOverview.ID, data.id)
        self.assertEqual(TemplateJokerOverview.NAME, data.name)
        self.assertEqual(TemplateJokerOverview.DESCRIPTION, data.description)
        self.assertEqual(TemplateJokerOverview.create_exports, data.create_method)

    def test_getTemplates_noHomeDeliveryLocation_homeDeliveryTemplateNotIncluded(
        self,
    ):
        cache = self._build_cache(
            [PickupLocationFactory.build(id="normal", is_home_delivery=False)]
        )

        result = CsvExportTemplateManager.get_templates(cache=cache)

        self.assertNotIn(TemplateHomeDeliveryList.ID, result)

    def test_getTemplates_homeDeliveryLocationExists_homeDeliveryTemplateIncluded(
        self,
    ):
        cache = self._build_cache(
            [
                PickupLocationFactory.build(id="normal", is_home_delivery=False),
                PickupLocationFactory.build(id="home", is_home_delivery=True),
            ]
        )

        result = CsvExportTemplateManager.get_templates(cache=cache)

        self.assertIn(TemplateHomeDeliveryList.ID, result)

    def test_createExportsFromTemplate_templateIdNotFound_raises404(self):
        with self.assertRaisesMessage(
            Http404,
            "Unknown template id \"unknown\", available IDs: ['member_list_geng', 'joker_overview', 'payments_by_income_source']",
        ):
            CsvExportTemplateManager.create_exports_from_template(
                template_id="unknown", cache=self._build_cache([])
            )
