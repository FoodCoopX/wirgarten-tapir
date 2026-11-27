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


@override_settings(
    KEYCLOAK_USERNAME_SOURCE="email",
    KEYCLOAK_USERNAME_FORMAT="raw",
    KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[],
)
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

    @override_settings(
        KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[
            {"keycloak": "customernumber", "tapir": "member_no"}
        ]
    )
    def test_createKeycloakUser_attributeMap_includesAttribute(self):
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
        self.assertEqual({"customernumber": ["17"]}, data["attributes"])

    @override_settings(
        KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[
            {"keycloak": "customernumber", "tapir": "member_no"}
        ]
    )
    def test_createKeycloakUser_attributeMapWithoutMemberNumber_hasNoAttribute(
        self,
    ):
        member = Member.objects.create(
            first_name="Jane",
            last_name="Doe",
            email="user@example.com",
            username="user@example.com",
            member_no=None,
        )

        KeycloakUserManager.create_keycloak_user_if_necessary(
            user=member, initial_password=None
        )

        data = self.mock_keycloak_client.create_user.call_args.args[0]
        self.assertNotIn("attributes", data)

    def test_updateKeycloakUserAttributes_default_mergesAndRemoves(self):
        with self.settings(KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[]):
            member = MemberFactory.create(member_no=17)
            KeycloakUserManager.create_keycloak_user_if_necessary(
                user=member, initial_password=None
            )

        with self.settings(
            KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[
                {"keycloak": "customernumber", "tapir": "member_no"}
            ]
        ):
            KeycloakUserManager.update_keycloak_user_attributes(member)
        call = self.mock_keycloak_client.update_user.call_args
        self.assertEqual(member.keycloak_id, call.kwargs["user_id"])
        self.assertEqual(
            {"customernumber": ["17"]}, call.kwargs["payload"]["attributes"]
        )
        self.assertEqual(member.email, call.kwargs["payload"]["email"])

        member.member_no = None
        member.save()
        with self.settings(
            KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[
                {"keycloak": "customernumber", "tapir": "member_no"}
            ]
        ):
            KeycloakUserManager.update_keycloak_user_attributes(member)
        call = self.mock_keycloak_client.update_user.call_args
        self.assertEqual(member.keycloak_id, call.kwargs["user_id"])
        self.assertEqual({}, call.kwargs["payload"]["attributes"])
        self.assertEqual(member.email, call.kwargs["payload"]["email"])

    @override_settings(
        KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[
            {"keycloak": "customernumber", "tapir": "member_no"}
        ]
    )
    @patch.object(KeycloakUserManager, "update_keycloak_user_attributes", autospec=True)
    def test_createKeycloakUser_existingKeycloakId_updatesAttributes(
        self, mock_update_keycloak_user_attributes
    ):
        member = MemberFactory.create(keycloak_id="existing-id", member_no=17)

        KeycloakUserManager.create_keycloak_user_if_necessary(
            user=member, initial_password=None
        )

        mock_update_keycloak_user_attributes.assert_called_once_with(member)
