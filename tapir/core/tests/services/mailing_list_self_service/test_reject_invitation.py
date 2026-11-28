from django.test import override_settings
from rest_framework.exceptions import ValidationError

from tapir.core.services.mailman.mailing_list_self_service import (
    MailingListSelfService,
)
from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@override_settings(MAILING_LIST_DOMAIN="example.com")
class TestRejectInvitation(TapirUnitTest):
    def test_rejectInvitation_addressIsInvited_rejectsTheAddressRequest(self):
        mailing_list = MailmanTestHelper.build_mock_list(
            MockMailingListData(
                name="list",
                unconfirmed_recipients=["other@example.com", "a@example.com"],
            )
        )

        MailingListSelfService.reject_invitation(
            email="a@example.com", mailing_list=mailing_list
        )

        mailing_list.reject_request.assert_called_once_with(
            request_id=mailing_list.requests[1]["token"]
        )

    def test_rejectInvitation_addressIsNotInvited_raisesValidationError(self):
        mailing_list = MailmanTestHelper.build_mock_list(
            MockMailingListData(name="list")
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Die Adresse a@example.com ist nicht zu list@example.com eingeladen",
        ):
            MailingListSelfService.reject_invitation(
                email="a@example.com", mailing_list=mailing_list
            )

        mailing_list.reject_request.assert_not_called()
