from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.service.member import create_wait_list_entry
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCreateWaitListEntry(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_createWaitListEntry_mixedCaseAddress_storesTheNormalisedAddress(self):
        entry = create_wait_list_entry(
            member=None,
            first_name="John",
            last_name="Doe",
            email=" John@Example.com",
            phone_number="",
            street="",
            street_2="",
            postcode="",
            city="",
        )

        entry.refresh_from_db()
        self.assertEqual("john@example.com", entry.email)
