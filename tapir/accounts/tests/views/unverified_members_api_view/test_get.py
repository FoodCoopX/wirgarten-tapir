from django.urls import reverse
from rest_framework import status

from tapir.accounts.services.unverified_members_service import (
    UnverifiedMembersService,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestUnverifiedMembersApiViewGet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(reverse("accounts:unverified_members"))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_default_returnsActiveUnverifiedMembersAndEstimate(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
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

        response = self.client.get(reverse("accounts:unverified_members"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            {
                "members": [
                    {
                        "id": with_account.id,
                        "member_no": 12,
                        "first_name": with_account.first_name,
                        "last_name": with_account.last_name,
                        "email": with_account.email,
                        "has_keycloak_account": True,
                        "profile_url": f"/tapir/members/{with_account.id}",
                    },
                    {
                        "id": without_account.id,
                        "member_no": 13,
                        "first_name": without_account.first_name,
                        "last_name": without_account.last_name,
                        "email": without_account.email,
                        "has_keycloak_account": False,
                        "profile_url": f"/tapir/members/{without_account.id}",
                    },
                ],
                "estimated_duration_seconds": 2
                * UnverifiedMembersService.SECONDS_BETWEEN_MAILS,
                "sending_in_progress": False,
            },
            response.json(),
        )
