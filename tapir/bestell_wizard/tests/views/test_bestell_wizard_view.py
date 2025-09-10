from django.urls import reverse

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBestellWizardView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_notLoggedIn_viewIsAccessible(self):
        response = self.client.get(reverse("bestell_wizard:bestell_wizard"))
        self.assertStatusCode(response, 200)
