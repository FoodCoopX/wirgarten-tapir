from django.urls import reverse

from tapir.bestell_wizard.serializers import PersonalDataSerializer
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBestellWizardView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_notLoggedIn_viewIsAccessible(self):
        response = self.client.get(reverse("bestell_wizard:bestell_wizard"))
        self.assertStatusCode(response, 200)

    def test_get_pageDoesNotOfferAPseudonymField(self):
        # The pseudonym is set from the member profile after signup, on
        # neither the direct-signup nor the waiting-list path.
        response = self.client.get(reverse("bestell_wizard:bestell_wizard"))

        self.assertNotIn(b"data-pseudonym-enabled", response.content)

    def test_personalDataSerializer_ignoresASubmittedPseudonym(self):
        serializer = PersonalDataSerializer(
            data={
                "first_name": "Anna",
                "last_name": "Muster",
                "email": "anna@example.net",
                "phone_number": "0123",
                "street": "Hauptstr. 1",
                "street_2": "",
                "postcode": "12345",
                "city": "Musterstadt",
                "country": "DE",
                "account_owner": "",
                "iban": "",
                "pseudonym": "Brotfreundin",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("pseudonym", serializer.validated_data)
