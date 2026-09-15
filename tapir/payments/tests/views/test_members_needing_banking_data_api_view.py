import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMembersNeedingBankingDataApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.get(reverse("payments:members_needing_banking_data"))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_loggedInAsAdmin_returns200(self):
        admin = self._create_member_with_complete_banking_data(is_superuser=True)
        self.client.force_login(admin)

        response = self.client.get(reverse("payments:members_needing_banking_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_get_default_missingIban_isReturnedWithCorrectFields(self):
        admin = self._create_member_with_complete_banking_data(is_superuser=True)
        self.client.force_login(admin)

        member = self._create_member_with_complete_banking_data(
            first_name="Anna",
            last_name="Müller",
            email="anna@example.com",
            phone_number="+491234567",
            member_no=42,
            iban=None,
        )

        response = self.client.get(reverse("payments:members_needing_banking_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(1, len(response_content))
        self.assertEqual(
            {
                "member_no": 42,
                "first_name": "Anna",
                "last_name": "Müller",
                "email": "anna@example.com",
                "phone_number": "+491234567",
                "member_url": member.get_absolute_url(),
            },
            response_content[0],
        )

    def test_get_default_missingAccountOwner_isReturned(self):
        admin = self._create_member_with_complete_banking_data(is_superuser=True)
        self.client.force_login(admin)
        self._create_member_with_complete_banking_data(
            first_name="Bob", account_owner=""
        )

        response = self.client.get(reverse("payments:members_needing_banking_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertIn("Bob", {entry["first_name"] for entry in response.json()})

    def test_get_default_missingSepaConsent_isReturned(self):
        admin = self._create_member_with_complete_banking_data(is_superuser=True)
        self.client.force_login(admin)
        self._create_member_with_complete_banking_data(
            first_name="Carla", sepa_consent=None
        )

        response = self.client.get(reverse("payments:members_needing_banking_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertIn("Carla", {entry["first_name"] for entry in response.json()})

    def test_get_default_completeBankingData_isNotReturned(self):
        admin = self._create_member_with_complete_banking_data(is_superuser=True)
        self.client.force_login(admin)
        self._create_member_with_complete_banking_data(first_name="Dana")

        response = self.client.get(reverse("payments:members_needing_banking_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual([], response.json())

    @staticmethod
    def _create_member_with_complete_banking_data(**kwargs):
        kwargs.setdefault("iban", "DE89370400440532013000")
        kwargs.setdefault("account_owner", "Test Owner")
        kwargs.setdefault(
            "sepa_consent",
            datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc),
        )
        return MemberFactory.create(**kwargs)
