from unittest.mock import MagicMock, Mock, patch

from django.test import override_settings

from tapir.core.services.former_member_address_provider import (
    FormerMemberAddressProvider,
)
from tapir.core.services.mailman.former_member_list_unsubscriber import (
    FormerMemberListUnsubscriber,
)
from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.models import MemberUnsubscribedFromMailingListsLogEntry
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(MAILING_LISTS_ENABLED=True, MAILING_LIST_DOMAIN="example.com")
@patch.object(
    FormerMemberAddressProvider, "get_former_member_by_address", autospec=True
)
class TestUnsubscribeFormerMembers(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_unsubscribeFormerMembers_default_removesFormerAddressesAndLogsOncePerMember(
        self, mock_get_former_member_by_address: MagicMock
    ):
        former_member = MemberFactory.create()
        mock_get_former_member_by_address.return_value = {
            "former@example.com": former_member,
            "former.extra@example.com": former_member,
        }
        subscribed_list, invited_list = self._mock_lists(
            MockMailingListData(
                name="subscribed",
                confirmed_recipients=["former@example.com", "active@example.com"],
            ),
            MockMailingListData(
                name="invited", unconfirmed_recipients=["former.extra@example.com"]
            ),
        )

        FormerMemberListUnsubscriber.unsubscribe_former_members(cache={})

        subscribed_list.unsubscribe.assert_called_once_with(
            email="former@example.com", pre_confirmed=True, pre_approved=True
        )
        invited_list.discard_request.assert_called_once_with(
            request_id=invited_list.requests[0]["token"]
        )
        log_entry = MemberUnsubscribedFromMailingListsLogEntry.objects.get()
        self.assertEqual(former_member.id, log_entry.user_id)
        self.assertIsNone(log_entry.actor)
        self.assertEqual(
            [
                "former@example.com: von subscribed@example.com abgemeldet",
                "former.extra@example.com: Anfrage für invited@example.com verworfen",
            ],
            log_entry.removals,
        )

    def test_unsubscribeFormerMembers_nothingToRemove_logsNothing(
        self, mock_get_former_member_by_address: MagicMock
    ):
        mock_get_former_member_by_address.return_value = {
            "former@example.com": MemberFactory.create()
        }
        mailing_list = self._mock_lists(
            MockMailingListData(
                name="list", confirmed_recipients=["active@example.com"]
            )
        )[0]

        FormerMemberListUnsubscriber.unsubscribe_former_members(cache={})

        mailing_list.unsubscribe.assert_not_called()
        self.assertFalse(MemberUnsubscribedFromMailingListsLogEntry.objects.exists())

    def test_unsubscribeFormerMembers_laterListFails_logsEarlierRemovalsAndRaises(
        self, mock_get_former_member_by_address: MagicMock
    ):
        former_member = MemberFactory.create()
        mock_get_former_member_by_address.return_value = {
            "former@example.com": former_member
        }
        failing_list = self._mock_lists(
            MockMailingListData(
                name="first", confirmed_recipients=["former@example.com"]
            ),
            MockMailingListData(
                name="second", confirmed_recipients=["former@example.com"]
            ),
        )[1]
        failing_list.unsubscribe.side_effect = RuntimeError("Mailman unreachable")

        with self.assertRaisesMessage(RuntimeError, "Mailman unreachable"):
            FormerMemberListUnsubscriber.unsubscribe_former_members(cache={})

        log_entry = MemberUnsubscribedFromMailingListsLogEntry.objects.get()
        self.assertEqual(former_member.id, log_entry.user_id)
        self.assertEqual(
            ["former@example.com: von first@example.com abgemeldet"],
            log_entry.removals,
        )

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_unsubscribeFormerMembers_mailingListsDisabled_doesNothing(
        self, mock_get_former_member_by_address: MagicMock
    ):
        FormerMemberListUnsubscriber.unsubscribe_former_members(cache={})

        mock_get_former_member_by_address.assert_not_called()

    def _mock_lists(self, *mailing_list_datas: MockMailingListData) -> list[Mock]:
        return MailmanTestHelper.mock_domain(
            test=self, mailing_list_datas=list(mailing_list_datas)
        ).lists
