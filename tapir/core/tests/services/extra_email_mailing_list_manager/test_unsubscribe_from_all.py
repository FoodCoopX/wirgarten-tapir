from unittest.mock import Mock

from django.test import override_settings
from django.utils import timezone

from tapir.core.services.mailman.extra_email_mailing_list_manager import (
    ExtraEmailMailingListManager,
)
from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(MAILING_LISTS_ENABLED=True, MAILING_LIST_DOMAIN="example.com")
class TestUnsubscribeFromAll(TapirIntegrationTest):
    ADDRESS = "extra@example.com"

    def test_unsubscribeFromAll_default_unsubscribesAndDiscardsPendingRequests(self):
        domain = self._mock_domain()

        ExtraEmailMailingListManager.unsubscribe_from_all(email=self.ADDRESS, cache={})

        subscribed_list, invited_list, other_list = domain.lists
        subscribed_list.unsubscribe.assert_called_once_with(
            email=self.ADDRESS, pre_confirmed=True, pre_approved=True
        )
        subscribed_list.discard_request.assert_not_called()
        invited_list.unsubscribe.assert_not_called()
        invited_list.discard_request.assert_called_once_with(
            request_id=invited_list.requests[0]["token"]
        )
        other_list.unsubscribe.assert_not_called()
        other_list.discard_request.assert_not_called()

    def test_unsubscribeFromAll_addressIsAMainAddress_doesNothing(self):
        MemberFactory.create(email=self.ADDRESS)
        domain = self._mock_domain()

        ExtraEmailMailingListManager.unsubscribe_from_all(email=self.ADDRESS, cache={})

        self._assert_nothing_changed(domain)

    def test_unsubscribeFromAll_addressIsAConfirmedExtraOfAnotherMember_doesNothing(
        self,
    ):
        MemberExtraEmailFactory.create(email=self.ADDRESS, confirmed_on=timezone.now())
        domain = self._mock_domain()

        ExtraEmailMailingListManager.unsubscribe_from_all(email=self.ADDRESS, cache={})

        self._assert_nothing_changed(domain)

    def test_unsubscribeFromAll_addressIsAnUnconfirmedExtraOfAnotherMember_unsubscribes(
        self,
    ):
        MemberExtraEmailFactory.create(email=self.ADDRESS, confirmed_on=None)
        domain = self._mock_domain()

        ExtraEmailMailingListManager.unsubscribe_from_all(email=self.ADDRESS, cache={})

        domain.lists[0].unsubscribe.assert_called_once_with(
            email=self.ADDRESS, pre_confirmed=True, pre_approved=True
        )

    @override_settings(MAILING_LISTS_ENABLED=False)
    def test_unsubscribeFromAll_mailingListsDisabled_doesNothing(self):
        domain = self._mock_domain()

        ExtraEmailMailingListManager.unsubscribe_from_all(email=self.ADDRESS, cache={})

        self._assert_nothing_changed(domain)

    def _mock_domain(self) -> Mock:
        return MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="subscribed",
                    confirmed_recipients=[self.ADDRESS, "other@example.com"],
                ),
                MockMailingListData(
                    name="invited",
                    unconfirmed_recipients=[self.ADDRESS, "other@example.com"],
                ),
                MockMailingListData(
                    name="other",
                    confirmed_recipients=["other@example.com"],
                    unconfirmed_recipients=["other@example.com"],
                ),
            ],
        )

    @staticmethod
    def _assert_nothing_changed(domain: Mock):
        for mailing_list in domain.lists:
            mailing_list.unsubscribe.assert_not_called()
            mailing_list.discard_request.assert_not_called()
