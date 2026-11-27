from unittest.mock import MagicMock, patch

from tapir.core.services.mailman.former_member_list_unsubscriber import (
    FormerMemberListUnsubscriber,
)
from tapir.core.tasks import unsubscribe_former_members_from_mailing_lists
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestUnsubscribeFormerMembersFromMailingLists(TapirUnitTest):
    @patch.object(
        FormerMemberListUnsubscriber, "unsubscribe_former_members", autospec=True
    )
    def test_unsubscribeFormerMembersFromMailingLists_default_runsTheUnsubscriber(
        self, mock_unsubscribe_former_members: MagicMock
    ):
        unsubscribe_former_members_from_mailing_lists()

        mock_unsubscribe_former_members.assert_called_once_with(cache={})
