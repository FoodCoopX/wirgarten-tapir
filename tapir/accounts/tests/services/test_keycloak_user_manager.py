from unittest.mock import patch

from django.test import override_settings

from tapir.accounts.models import TapirUser
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.accounts.services.keycloak_username_service import (
    KeycloakUsernameUnavailable,
)
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.models import Member
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestKeycloakUserManager(TapirIntegrationTest):
    @override_settings(KEYCLOAK_USERNAME_SOURCE="email")
    def test_createKeycloakUser_emailSource_usesEmail(self):
        member = MemberFactory.create(
            first_name="Jane",
            last_name="Doe",
            email="user@example.com",
            member_no=17,
        )

        KeycloakUserManager.create_keycloak_user_if_necessary(
            user=member, initial_password=None
        )

        data = self.mock_keycloak_client.create_user.call_args.args[0]
        self.assertEqual("user@example.com", data["username"])
        self.assertEqual("user@example.com", data["email"])
        self.assertNotIn("attributes", data)
        self.assertIsNotNone(member.keycloak_id)
        self.assertEqual("user@example.com", member.username)

    @override_settings(
        KEYCLOAK_USERNAME_SOURCE="customernumber",
        KEYCLOAK_USERNAME_FORMAT="raw",
    )
    def test_createKeycloakUser_customernumberRaw_usesNumber(self):
        member = MemberFactory.create(
            first_name="Jane",
            last_name="Doe",
            email="user@example.com",
            member_no=17,
        )

        KeycloakUserManager.create_keycloak_user_if_necessary(
            user=member, initial_password=None
        )

        data = self.mock_keycloak_client.create_user.call_args.args[0]
        self.assertEqual("17", data["username"])
        self.assertEqual("user@example.com", data["email"])
        self.assertNotIn("attributes", data)
        self.assertEqual("user@example.com", member.username)

    @override_settings(
        KEYCLOAK_USERNAME_SOURCE="customernumber",
        KEYCLOAK_USERNAME_FORMAT="formatted",
    )
    @patch.object(MemberNumberService, "format_member_number", return_value="BT0017")
    def test_createKeycloakUser_customernumberFormatted_usesFormattedNumber(
        self, _format_member_number
    ):
        member = MemberFactory.create(
            first_name="Jane",
            last_name="Doe",
            email="user@example.com",
            member_no=17,
        )

        KeycloakUserManager.create_keycloak_user_if_necessary(
            user=member, initial_password=None
        )

        self.assertEqual(
            "BT0017",
            self.mock_keycloak_client.create_user.call_args.args[0]["username"],
        )

    @override_settings(KEYCLOAK_USERNAME_SOURCE="customernumber")
    def test_createKeycloakUser_memberWithoutNumber_raises(self):
        member = Member.objects.create(
            first_name="Jane",
            last_name="Doe",
            email="user@example.com",
            username="user@example.com",
            member_no=None,
        )

        with self.assertRaises(KeycloakUsernameUnavailable):
            KeycloakUserManager.create_keycloak_user_if_necessary(
                user=member, initial_password=None
            )

        self.mock_keycloak_client.create_user.assert_not_called()
        self.assertIsNone(member.keycloak_id)

    @override_settings(KEYCLOAK_USERNAME_SOURCE="customernumber")
    def test_createKeycloakUser_nonMember_usesEmail(self):
        user = TapirUser.objects.create(
            first_name="Admin",
            last_name="User",
            email="admin@example.com",
            username="admin@example.com",
        )

        KeycloakUserManager.create_keycloak_user_if_necessary(
            user=user, initial_password=None
        )

        data = self.mock_keycloak_client.create_user.call_args.args[0]
        self.assertEqual("admin@example.com", data["username"])
        self.assertEqual("admin@example.com", data["email"])
        self.assertNotIn("attributes", data)

    def test_createKeycloakUser_existingKeycloakId_doesNothing(self):
        member = MemberFactory.create(keycloak_id="existing-id")

        KeycloakUserManager.create_keycloak_user_if_necessary(
            user=member, initial_password=None
        )

        self.mock_keycloak_client.create_user.assert_not_called()
        self.assertEqual("existing-id", member.keycloak_id)
