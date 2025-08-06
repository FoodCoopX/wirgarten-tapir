import datetime
import uuid

from django.urls import reverse
from rest_framework import status

from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPublicGetWaitingListEntryDetails(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_entryIdIsCorrectButLinkKeyIsInvalid_returns404(self):
        entry = WaitingListEntryFactory.create(confirmation_link_key=uuid.uuid4())

        url = reverse("waiting_list:public_get_waiting_list_entry_details")
        url = f"{url}?entry_id={entry.id}&link_key=test_key"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_get_entryHasNoMember_birthdateAndBankingFieldsAreEmpty(self):
        entry = WaitingListEntryFactory.create(confirmation_link_key=uuid.uuid4())

        url = reverse("waiting_list:public_get_waiting_list_entry_details")
        url = f"{url}?entry_id={entry.id}&link_key={entry.confirmation_link_key}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertIsNone(response_content["birthdate"])
        self.assertIsNone(response_content["account_owner"])
        self.assertIsNone(response_content["iban"])

    def test_get_entryHasAMember_birthdateAndBankingFieldsAreFilled(self):
        member = MemberFactory.create(
            birthdate=datetime.date(year=1990, month=12, day=22),
            account_owner="Bart Simpson",
            iban="NL35ABNA7806242643",
        )
        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(), member=member
        )

        url = reverse("waiting_list:public_get_waiting_list_entry_details")
        url = f"{url}?entry_id={entry.id}&link_key={entry.confirmation_link_key}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertEqual("1990-12-22", response_content["birthdate"])
        self.assertEqual("Bart Simpson", response_content["account_owner"])
        self.assertEqual("NL35ABNA7806242643", response_content["iban"])
