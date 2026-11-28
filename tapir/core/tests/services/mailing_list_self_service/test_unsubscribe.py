from django.test import override_settings
from rest_framework.exceptions import ValidationError

from tapir.core.services.mailman.mailing_list_self_service import (
    MailingListSelfService,
)
from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@override_settings(MAILING_LIST_DOMAIN="example.com")
class TestUnsubscribe(TapirUnitTest):
    def test_unsubscribe_addressIsSubscribed_unsubscribes(self):
        mailing_list = MailmanTestHelper.build_mock_list(
            MockMailingListData(name="list", confirmed_recipients=["a@example.com"])
        )

        MailingListSelfService.unsubscribe(
            email="a@example.com", mailing_list=mailing_list
        )

        mailing_list.unsubscribe.assert_called_once_with(
            email="a@example.com", pre_confirmed=True, pre_approved=True
        )

    def test_unsubscribe_addressIsNotSubscribed_raisesValidationError(self):
        mailing_list = MailmanTestHelper.build_mock_list(
            MockMailingListData(name="list")
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Die Adresse a@example.com ist nicht zu list@example.com angemeldet",
        ):
            MailingListSelfService.unsubscribe(
                email="a@example.com", mailing_list=mailing_list
            )

        mailing_list.unsubscribe.assert_not_called()
