from unittest.mock import patch, MagicMock

from django.urls import reverse
from rest_framework import status

from tapir.accounts.services.unverified_members_service import (
    UnverifiedMembersService,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch("tapir.accounts.views.send_verification_emails.delay", autospec=True)
class TestUnverifiedMembersApiViewPost(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_loggedInAsNormalMember_returns403AndSendsNothing(
        self, mock_delay: MagicMock
    ):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.post(reverse("accounts:unverified_members"))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        mock_delay.assert_not_called()

    def test_post_default_startsTaskWithActiveUnverifiedMembers(
        self, mock_delay: MagicMock
    ):
        actor = MemberFactory.create(is_superuser=True)
        self.client.force_login(actor)
        verified = MemberFactory.create(keycloak_id="verified", member_no=11)
        with_account = MemberFactory.create(keycloak_id="unverified", member_no=12)
        without_account = MemberFactory.create(keycloak_id=None, member_no=13)
        MemberFactory.create(keycloak_id=None, member_no=14)
        for member in [verified, with_account, without_account]:
            AssociationMembershipFactory.create(member=member)
        self.mock_keycloak_client.get_users.return_value = [
            {"id": "verified", "emailVerified": True},
            {"id": "unverified", "emailVerified": False},
        ]

        response = self.client.post(reverse("accounts:unverified_members"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            {
                "member_count": 2,
                "estimated_duration_seconds": 2
                * UnverifiedMembersService.SECONDS_BETWEEN_MAILS,
            },
            response.json(),
        )
        mock_delay.assert_called_once_with(
            member_ids=[with_account.id, without_account.id], actor_id=actor.id
        )

    @patch.object(
        UnverifiedMembersService,
        "is_sending_in_progress",
        autospec=True,
        return_value=True,
    )
    def test_post_sendingInProgress_returns409AndStartsNoTask(
        self, _: MagicMock, mock_delay: MagicMock
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.post(reverse("accounts:unverified_members"))

        self.assertStatusCode(response, status.HTTP_409_CONFLICT)
        mock_delay.assert_not_called()
