from django.test import override_settings

from tapir.configuration.forms import ParameterForm
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestParameterForm(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @override_settings(BAKERY_ENABLED=False)
    def test_init_bakeryDisabled_bakeryCategoryIsHidden(self):
        form = ParameterForm()

        self.assertNotIn(ParameterCategory.BAKERY, form.categories)
        self.assertNotIn(ParameterKeys.BAKERY_STOVE_LAYERS, form.fields)

    @override_settings(BAKERY_ENABLED=True)
    def test_init_bakeryEnabled_bakeryCategoryIsShown(self):
        form = ParameterForm()

        self.assertIn(ParameterCategory.BAKERY, form.categories)
        self.assertIn(ParameterKeys.BAKERY_STOVE_LAYERS, form.fields)
