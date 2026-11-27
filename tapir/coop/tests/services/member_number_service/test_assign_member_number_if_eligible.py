from unittest.mock import patch

from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestAssignMemberNumberIfEligible(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_assignMemberNumberIfEligible_eligible_assignsNumberSavesAndReturnsTrue(
        self,
    ):
        member = MemberFactory.create()
        member.member_no = None
        member.save()

        result = MemberNumberService.assign_member_number_if_eligible(
            member, cache={}, actor=None
        )

        self.assertTrue(result)
        member.refresh_from_db()
        self.assertIsNotNone(member.member_no)
        self.assertTrue(UpdateTapirUserLogEntry.objects.exists())

    def test_assignMemberNumberIfEligible_notEligible_doesNothingAndReturnsFalse(self):
        member = MemberFactory.create(member_no=5)

        result = MemberNumberService.assign_member_number_if_eligible(
            member, cache={}, actor=None
        )

        self.assertFalse(result)
        member.refresh_from_db()
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    @patch.object(KeycloakUserManager, "update_keycloak_user_attributes")
    def test_assignMemberNumberIfEligible_withKeycloakId_schedulesAttributeUpdate(
        self, mock_update_keycloak_user_attributes
    ):
        member = MemberFactory.create()
        member.member_no = None
        member.keycloak_id = "keycloak-id"
        member.save()

        with self.settings(
            KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[
                {"keycloak": "customernumber", "tapir": "member_no"}
            ]
        ):
            with self.captureOnCommitCallbacks(execute=True):
                MemberNumberService.assign_member_number_if_eligible(
                    member, cache={}, actor=None
                )

        mock_update_keycloak_user_attributes.assert_called_once_with(member)

    @patch.object(KeycloakUserManager, "update_keycloak_user_attributes")
    def test_assignMemberNumberIfEligible_withoutAttributeMap_doesNotUpdateKeycloak(
        self, mock_update_keycloak_user_attributes
    ):
        member = MemberFactory.create()
        member.member_no = None
        member.keycloak_id = "keycloak-id"
        member.save()

        with self.settings(KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[]):
            with self.captureOnCommitCallbacks(execute=True):
                MemberNumberService.assign_member_number_if_eligible(
                    member, cache={}, actor=None
                )

        mock_update_keycloak_user_attributes.assert_not_called()
