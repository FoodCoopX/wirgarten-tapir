from unittest.mock import Mock

from django.test import override_settings

from tapir.core.services.mailman.mailing_list_address_mover import (
    MailingListAddressMover,
)
from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@override_settings(MAILING_LISTS_ENABLED=True, MAILING_LIST_DOMAIN="example.com")
class TestMoveSubscriptions(TapirUnitTest):
    OLD = "old@example.com"
    NEW = "new@example.com"

    def test_moveSubscriptions_oldAddressSubscribed_subscribesTheNewAddressWithoutWelcomeAndUnsubscribesTheOld(
        self,
    ):
        mailing_list = self._mock_lists(
            MockMailingListData(name="list", confirmed_recipients=[self.OLD])
        )[0]

        MailingListAddressMover.move_subscriptions(
            old_email=self.OLD, new_email=self.NEW, cache={}
        )

        mailing_list.subscribe.assert_called_once_with(
            address=self.NEW,
            pre_verified=True,
            pre_confirmed=True,
            pre_approved=True,
            send_welcome_message=False,
        )
        mailing_list.unsubscribe.assert_called_once_with(
            email=self.OLD, pre_confirmed=True, pre_approved=True
        )

    def test_moveSubscriptions_bothAddressesSubscribed_onlyUnsubscribesTheOld(self):
        mailing_list = self._mock_lists(
            MockMailingListData(name="list", confirmed_recipients=[self.OLD, self.NEW])
        )[0]

        MailingListAddressMover.move_subscriptions(
            old_email=self.OLD, new_email=self.NEW, cache={}
        )

        mailing_list.subscribe.assert_not_called()
        mailing_list.unsubscribe.assert_called_once_with(
            email=self.OLD, pre_confirmed=True, pre_approved=True
        )

    def test_moveSubscriptions_oldAddressInvited_discardsTheInvitation(self):
        invited_list, other_list = self._mock_lists(
            MockMailingListData(name="invited", unconfirmed_recipients=[self.OLD]),
            MockMailingListData(name="other", confirmed_recipients=[self.NEW]),
        )

        MailingListAddressMover.move_subscriptions(
            old_email=self.OLD, new_email=self.NEW, cache={}
        )

        invited_list.discard_request.assert_called_once_with(
            request_id=invited_list.requests[0]["token"]
        )
        invited_list.subscribe.assert_not_called()
        for mailing_list in [invited_list, other_list]:
            mailing_list.unsubscribe.assert_not_called()
        other_list.subscribe.assert_not_called()

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_moveSubscriptions_mailingListsDisabled_doesNothing(self):
        mailing_list = self._mock_lists(
            MockMailingListData(name="list", confirmed_recipients=[self.OLD])
        )[0]

        MailingListAddressMover.move_subscriptions(
            old_email=self.OLD, new_email=self.NEW, cache={}
        )

        mailing_list.subscribe.assert_not_called()
        mailing_list.unsubscribe.assert_not_called()

    def _mock_lists(self, *mailing_list_datas: MockMailingListData) -> list[Mock]:
        return MailmanTestHelper.mock_domain(
            test=self, mailing_list_datas=list(mailing_list_datas)
        ).lists
