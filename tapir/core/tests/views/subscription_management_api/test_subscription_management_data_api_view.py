from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.core.tests.mailman_test_helper import MailmanTestHelper, MockMailingListData
from tapir.mail.models import (
    ExternalRecipient,
    InternalRecipientCategoryRegistration,
    MailCategoryMode,
    StaticSegmentRecipient,
)
from tapir.mail.tests.factories import MailCategoryFactory, MailSegmentFactory
from tapir.mail.tests.test_utils import add_mail_segment_provider
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(MAILING_LISTS_ENABLED=False, MAILING_LIST_DOMAIN="example.com")
@patch.object(
    SubscriptionManagementTokenSigner,
    "get_address",
    autospec=True,
    return_value="address@example.com",
)
class TestSubscriptionManagementDataApiView(TapirIntegrationTest):
    SEGMENT = "segment"

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)
        add_mail_segment_provider(
            self,
            lambda: {
                self.SEGMENT: MailSegmentFactory.build(get_queryset=Member.objects.all)
            },
        )

    def test_get_tokenIsInvalid_returns403(self, mock_get_address: MagicMock):
        mock_get_address.return_value = None

        response = self._get()

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_addressIsAMainAddress_returns403(self, _: MagicMock):
        MemberFactory.create(email="address@example.com")

        response = self._get()

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_unknownAddress_returnsOnlyTheAddress(self, _: MagicMock):
        response = self._get()

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            {
                "address": "address@example.com",
                "extra": None,
                "external": None,
                "mailing_lists": None,
            },
            response.json(),
        )

    def test_get_addressIsAConfirmedExtra_returnsTheExtraPartWithTheExtraStates(
        self, _: MagicMock
    ):
        member = MemberFactory.create(first_name="Main")
        extra_email = MemberExtraEmailFactory.create(
            member=member,
            email="address@example.com",
            confirmed_on=timezone.now(),
            receives_direct_mails=False,
        )
        always_on = MailCategoryFactory.create(
            name="A", mode=MailCategoryMode.ALWAYS_ON, dynamic_segment_name=self.SEGMENT
        )
        default_off = MailCategoryFactory.create(
            name="B",
            mode=MailCategoryMode.OPTIONAL_DEFAULT_OFF,
            dynamic_segment_name=self.SEGMENT,
        )
        InternalRecipientCategoryRegistration.objects.create(
            member_extra_email=extra_email, mail_category=always_on, is_registered=False
        )

        response = self._get()

        self.assertEqual(
            {
                "member_first_name": "Main",
                "receives_direct_mails": False,
                "categories": [
                    {
                        "id": always_on.id,
                        "name": "A",
                        "mode": MailCategoryMode.ALWAYS_ON,
                    },
                    {
                        "id": default_off.id,
                        "name": "B",
                        "mode": MailCategoryMode.OPTIONAL_DEFAULT_OFF,
                    },
                ],
                "categories_registered_to": {
                    always_on.id: False,
                    default_off.id: False,
                },
            },
            response.json()["extra"],
        )

    def test_get_extraFeatureDisabled_returnsNoExtraPart(self, _: MagicMock):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=False)
        MemberExtraEmailFactory.create(
            email="address@example.com", confirmed_on=timezone.now()
        )

        response = self._get()

        self.assertIsNone(response.json()["extra"])

    def test_get_addressIsAnUnconfirmedExtra_returnsNoExtraPart(self, _: MagicMock):
        MemberExtraEmailFactory.create(email="address@example.com", confirmed_on=None)

        response = self._get()

        self.assertIsNone(response.json()["extra"])

    def test_get_addressIsAnExternalRecipient_returnsTheExternalPartWithThePublicCategories(
        self, _: MagicMock
    ):
        ExternalRecipient.objects.create(
            email="address@example.com", first_name="External"
        )
        registered = MailCategoryFactory.create(name="A")
        MailCategoryFactory.create(
            name="Members only", available_for_external_recipients=False
        )
        not_registered = MailCategoryFactory.create(name="B")
        StaticSegmentRecipient.objects.create(
            segment=registered.static_segment, email="address@example.com"
        )

        response = self._get()

        self.assertEqual(
            {
                "first_name": "External",
                "categories": [
                    {"id": registered.id, "name": "A", "mode": registered.mode},
                    {"id": not_registered.id, "name": "B", "mode": not_registered.mode},
                ],
                "categories_registered_to": {
                    registered.id: True,
                    not_registered.id: False,
                },
            },
            response.json()["external"],
        )

    @override_settings(MAILING_LISTS_ENABLED=True)
    def test_get_mailingListsEnabled_returnsTheListsOfTheAddress(self, _: MagicMock):
        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(
                    name="subscribed", confirmed_recipients=["address@example.com"]
                ),
                MockMailingListData(name="hidden"),
            ],
        )

        response = self._get()

        mailing_lists = response.json()["mailing_lists"]
        self.assertEqual(
            ["subscribed@example.com"],
            [mailing_list["name"] for mailing_list in mailing_lists["available_lists"]],
        )
        self.assertEqual(["subscribed@example.com"], mailing_lists["subscribed_lists"])

    @override_settings(MAILING_LISTS_ENABLED=True)
    def test_get_addressCannotSubscribe_hidesTheAdvertisedListsItIsNotOn(
        self, _: MagicMock
    ):
        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="advertised", advertised=True)
            ],
        )

        response = self._get()

        self.assertEqual([], response.json()["mailing_lists"]["available_lists"])

    @override_settings(MAILING_LISTS_ENABLED=True)
    def test_get_addressIsAnExternalRecipient_showsTheAdvertisedLists(
        self, _: MagicMock
    ):
        ExternalRecipient.objects.create(email="address@example.com", first_name="E")
        MailmanTestHelper.mock_domain(
            test=self,
            mailing_list_datas=[
                MockMailingListData(name="advertised", advertised=True)
            ],
        )

        response = self._get()

        self.assertEqual(
            ["advertised@example.com"],
            [
                mailing_list["name"]
                for mailing_list in response.json()["mailing_lists"]["available_lists"]
            ],
        )

    def _get(self):
        return self.client.get(
            reverse("core:subscription_management_data") + "?token=the_token"
        )
