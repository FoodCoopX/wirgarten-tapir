from django.http import Http404

from tapir.core.config import THEME_TEST
from tapir.generic_exports.services.csv_export_template_manager import (
    CsvExportTemplateManager,
)
from tapir.generic_exports.services.csv_templates.template_joker_overview import (
    TemplateJokerOverview,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestCsvExportTemplateManager(TapirUnitTest):
    def test_getTemplates_default_buildsTemplateDataCorrectly(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.ORGANISATION_THEME, value=THEME_TEST
        )

        result = CsvExportTemplateManager.get_templates()

        data = result[TemplateJokerOverview.ID]
        self.assertEqual(TemplateJokerOverview.ID, data.id)
        self.assertEqual(TemplateJokerOverview.NAME, data.name)
        self.assertEqual(TemplateJokerOverview.DESCRIPTION, data.description)
        self.assertEqual(TemplateJokerOverview.create_exports, data.create_method)

    def test_createExportsFromTemplate_templateIdNotFound_raises404(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.ORGANISATION_THEME, value=THEME_TEST
        )

        with self.assertRaises(Http404) as error:
            CsvExportTemplateManager.create_exports_from_template("unknown")

        self.assertEqual(
            "Unknown template id \"unknown\", available IDs: ['location_routes', 'joker_overview']",
            str(error.exception),
        )
