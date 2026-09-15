from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMembersWithoutIbanApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.get(reverse("payments:members_without_iban"))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_loggedInAsAdmin_returns200(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        response = self.client.get(reverse("payments:members_without_iban"))

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_get_default_onlyReturnsMembersWithoutIban(self):
        admin = MemberFactory.create(is_superuser=True, iban="DE89370400440532013000")
        self.client.force_login(admin)

        member_with_null_iban = MemberFactory.create(
            first_name="Anna",
            last_name="Müller",
            email="anna@example.com",
            phone_number="+491234567",
            iban=None,
            member_no=42,
        )
        member_with_empty_iban = MemberFactory.create(iban="")
        MemberFactory.create(iban="DE89370400440532013001")

        response = self.client.get(reverse("payments:members_without_iban"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_ids = {entry["first_name"] for entry in response.json()}
        self.assertIn(member_with_null_iban.first_name, response_ids)
        self.assertIn(member_with_empty_iban.first_name, response_ids)
        self.assertEqual(2, len(response.json()))

        entry = next(
            entry for entry in response.json() if entry["first_name"] == "Anna"
        )
        self.assertEqual(
            {
                "member_no": 42,
                "first_name": "Anna",
                "last_name": "Müller",
                "email": "anna@example.com",
                "phone_number": "+491234567",
                "member_url": member_with_null_iban.get_absolute_url(),
            },
            entry,
        )
