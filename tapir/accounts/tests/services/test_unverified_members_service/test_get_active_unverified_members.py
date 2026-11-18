from unittest.mock import patch, MagicMock

from tapir.accounts.services.unverified_members_service import (
    UnverifiedMembersService,
)
from tapir.generic_exports.services.member_segment_provider import (
    MemberSegmentProvider,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetActiveUnverifiedMembers(TapirIntegrationTest):
    @patch.object(MemberSegmentProvider, "get_queryset_active_members", autospec=True)
    def test_getActiveUnverifiedMembers_default_returnsActiveMembersWithoutVerifiedKeycloakAccount(
        self, mock_get_queryset_active_members: MagicMock
    ):
        MemberFactory.create(keycloak_id="verified", member_no=1)
        unverified = MemberFactory.create(keycloak_id="unverified", member_no=2)
        without_account = MemberFactory.create(keycloak_id=None, member_no=3)
        inactive = MemberFactory.create(keycloak_id=None, member_no=4)
        mock_get_queryset_active_members.return_value = Member.objects.exclude(
            id=inactive.id
        )
        self.mock_keycloak_client.get_users.return_value = [
            {"id": "verified", "emailVerified": True},
            {"id": "unverified", "emailVerified": False},
        ]

        cache = {}

        result = UnverifiedMembersService.get_active_unverified_members(cache=cache)

        self.assertEqual([unverified, without_account], result)
        mock_get_queryset_active_members.assert_called_once_with(cache=cache)
        self.mock_keycloak_client.get_users.assert_called_once_with(
            query={"briefRepresentation": True}
        )
