from unittest.mock import MagicMock, patch

from django.test import override_settings

from tapir.core.services.former_member_address_provider import (
    FormerMemberAddressProvider,
)
from tapir.core.services.mailman.mailing_list_self_service import (
    MailingListSelfService,
)
from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    FormerMemberAddressProvider,
    "is_former_member_address",
    autospec=True,
    return_value=False,
)
@override_settings(MAILING_LIST_DOMAIN="example.com")
class TestBuildListData(TapirUnitTest):
    ADDRESS = "address@example.com"

    def setUp(self):
        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="advertised", advertised=True),
                MockMailingListData(name="hidden"),
                MockMailingListData(
                    name="subscribed", confirmed_recipients=[self.ADDRESS]
                ),
                MockMailingListData(
                    name="invited", unconfirmed_recipients=[self.ADDRESS]
                ),
            ],
        )

    def test_buildListData_includeAdvertisedLists_showsAdvertisedSubscribedAndInvitedLists(
        self, _: MagicMock
    ):
        result = MailingListSelfService.build_list_data(
            email=self.ADDRESS, include_advertised_lists=True, cache={}
        )

        self.assertEqual(
            [
                "advertised@example.com",
                "subscribed@example.com",
                "invited@example.com",
            ],
            [mailing_list["name"] for mailing_list in result["available_lists"]],
        )
        self.assertEqual(["subscribed@example.com"], result["subscribed_lists"])
        self.assertEqual(
            ["invited@example.com"], result["waiting_for_confirmation_lists"]
        )

    def test_buildListData_excludeAdvertisedLists_showsOnlySubscribedAndInvitedLists(
        self, _: MagicMock
    ):
        result = MailingListSelfService.build_list_data(
            email=self.ADDRESS, include_advertised_lists=False, cache={}
        )

        self.assertEqual(
            ["subscribed@example.com", "invited@example.com"],
            [mailing_list["name"] for mailing_list in result["available_lists"]],
        )

    def test_buildListData_addressBelongsToAFormerMember_hidesAdvertisedListsAndFlagsIt(
        self, mock_is_former_member_address: MagicMock
    ):
        mock_is_former_member_address.return_value = True

        result = MailingListSelfService.build_list_data(
            email=self.ADDRESS, include_advertised_lists=True, cache={}
        )

        self.assertTrue(result["belongs_to_former_member"])
        self.assertEqual(
            ["subscribed@example.com", "invited@example.com"],
            [mailing_list["name"] for mailing_list in result["available_lists"]],
        )
