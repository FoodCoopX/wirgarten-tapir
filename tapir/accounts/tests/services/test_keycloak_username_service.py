from unittest.mock import patch

from django.test import override_settings

from tapir.accounts.models import TapirUser
from tapir.accounts.services.keycloak_username_service import (
    KeycloakUsernameService,
    KeycloakUsernameUnavailable,
)
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.models import Member
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestKeycloakUsernameService(TapirUnitTest):
    @override_settings(KEYCLOAK_USERNAME_SOURCE="email")
    def test_buildUsername_emailSource_returnsEmail(self):
        member = Member(email="user@example.com", member_no=17)

        self.assertEqual(
            "user@example.com", KeycloakUsernameService.build_username(member)
        )

    @override_settings(
        KEYCLOAK_USERNAME_SOURCE="customernumber",
        KEYCLOAK_USERNAME_FORMAT="raw",
    )
    def test_buildUsername_customernumberRaw_returnsNumber(self):
        member = Member(email="user@example.com", member_no=17)

        self.assertEqual("17", KeycloakUsernameService.build_username(member))

    @override_settings(
        KEYCLOAK_USERNAME_SOURCE="customernumber",
        KEYCLOAK_USERNAME_FORMAT="formatted",
    )
    @patch.object(MemberNumberService, "format_member_number", return_value="BT0017")
    def test_buildUsername_customernumberFormatted_returnsFormattedNumber(
        self, _format_member_number
    ):
        member = Member(email="user@example.com", member_no=17)

        self.assertEqual("BT0017", KeycloakUsernameService.build_username(member))

    @override_settings(KEYCLOAK_USERNAME_SOURCE="customernumber")
    def test_buildUsername_memberWithoutNumber_raises(self):
        member = Member(email="user@example.com", member_no=None)

        with self.assertRaises(KeycloakUsernameUnavailable):
            KeycloakUsernameService.build_username(member)

    @override_settings(KEYCLOAK_USERNAME_SOURCE="customernumber")
    def test_buildUsername_nonMember_returnsEmail(self):
        user = TapirUser(email="admin@example.com")

        self.assertEqual(
            "admin@example.com", KeycloakUsernameService.build_username(user)
        )

    @override_settings(KEYCLOAK_USERNAME_SOURCE="customernumber")
    def test_canCreateKeycloakUser_memberWithoutNumber_returnsFalse(self):
        member = Member(email="user@example.com", member_no=None)

        self.assertFalse(KeycloakUsernameService.can_create_keycloak_user(member))

    @override_settings(KEYCLOAK_USERNAME_SOURCE="customernumber")
    def test_canCreateKeycloakUser_nonMember_returnsTrue(self):
        user = TapirUser(email="admin@example.com")

        self.assertTrue(KeycloakUsernameService.can_create_keycloak_user(user))

    @override_settings(KEYCLOAK_USERNAME_SOURCE="customernumber")
    def test_usesEmailUsername_cases(self):
        member_with_number = Member(email="member@example.com", member_no=17)
        member_without_number = Member(email="member@example.com", member_no=None)
        user = TapirUser(email="admin@example.com")

        self.assertFalse(
            KeycloakUsernameService.uses_email_username(member_with_number)
        )
        self.assertTrue(
            KeycloakUsernameService.uses_email_username(member_without_number)
        )
        self.assertTrue(KeycloakUsernameService.uses_email_username(user))
