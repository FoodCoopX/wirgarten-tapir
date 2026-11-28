from unittest.mock import MagicMock, patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.mail.models import (
    InternalRecipientCategoryRegistration,
    MailCategoryMode,
)
from tapir.mail.tests.factories import MailCategoryFactory, MailSegmentFactory
from tapir.mail.tests.test_utils import add_mail_segment_provider
from tapir.wirgarten.models import (
    Member,
    MemberExtraEmail,
    MemberExtraEmailSubscriptionsChangedLogEntry,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(
    SubscriptionManagementTokenSigner,
    "get_address",
    autospec=True,
    return_value="extra@example.com",
)
class TestSubscriptionManagementExtraCategoriesApiView(TapirIntegrationTest):
    SEGMENT_WITH_MEMBER = "segment_with_member"
    SEGMENT_WITHOUT_MEMBER = "segment_without_member"

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)
        add_mail_segment_provider(
            self,
            lambda: {
                self.SEGMENT_WITH_MEMBER: MailSegmentFactory.build(
                    get_queryset=Member.objects.all
                ),
                self.SEGMENT_WITHOUT_MEMBER: MailSegmentFactory.build(
                    get_queryset=Member.objects.none
                ),
            },
        )

    def test_post_tokenIsInvalid_returns403(self, mock_get_address: MagicMock):
        mock_get_address.return_value = None

        response = self._post(categories_registered_to={})

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_post_featureDisabled_returns400(self, _: MagicMock):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=False)
        self._create_extra_email()

        response = self._post(categories_registered_to={})

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(["Diese Funktion ist ausgeschaltet."], response.json())

    def test_post_addressIsNotAConfirmedExtra_returns404(self, _: MagicMock):
        MemberExtraEmailFactory.create(email="extra@example.com", confirmed_on=None)

        response = self._post(categories_registered_to={})

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_post_default_updatesTheSubmittedCategoriesKeepsTheOthersAndLogsTheChanges(
        self, _: MagicMock
    ):
        extra_email = self._create_extra_email()
        changed = MailCategoryFactory.create(
            name="Changed",
            mode=MailCategoryMode.ALWAYS_ON,
            dynamic_segment_name=self.SEGMENT_WITH_MEMBER,
        )
        unchanged = MailCategoryFactory.create(
            name="Unchanged",
            mode=MailCategoryMode.OPTIONAL_DEFAULT_OFF,
            dynamic_segment_name=self.SEGMENT_WITH_MEMBER,
        )
        outside_segment = MailCategoryFactory.create(
            dynamic_segment_name=self.SEGMENT_WITHOUT_MEMBER
        )
        InternalRecipientCategoryRegistration.objects.create(
            member_extra_email=extra_email,
            mail_category=outside_segment,
            is_registered=True,
        )

        response = self._post(
            categories_registered_to={changed.id: False, unchanged.id: False}
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            {changed.id: False, unchanged.id: False, outside_segment.id: True},
            dict(
                InternalRecipientCategoryRegistration.objects.filter(
                    member_extra_email=extra_email
                ).values_list("mail_category_id", "is_registered")
            ),
        )
        log_entry = MemberExtraEmailSubscriptionsChangedLogEntry.objects.get()
        self.assertEqual("extra@example.com", log_entry.email)
        self.assertEqual(["Kategorie Changed: abgemeldet"], log_entry.changes)
        self.assertEqual(extra_email.member_id, log_entry.user_id)
        self.assertIsNone(log_entry.actor)

    def test_post_nothingChanged_logsNothing(self, _: MagicMock):
        self._create_extra_email()
        category = MailCategoryFactory.create(
            mode=MailCategoryMode.OPTIONAL_DEFAULT_ON,
            dynamic_segment_name=self.SEGMENT_WITH_MEMBER,
        )

        self._post(categories_registered_to={category.id: True})

        self.assertFalse(MemberExtraEmailSubscriptionsChangedLogEntry.objects.exists())

    def test_post_categoryOutsideTheMemberSegments_returns400(self, _: MagicMock):
        self._create_extra_email()
        outside_segment = MailCategoryFactory.create(
            dynamic_segment_name=self.SEGMENT_WITHOUT_MEMBER
        )

        response = self._post(categories_registered_to={outside_segment.id: True})

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(InternalRecipientCategoryRegistration.objects.exists())

    @staticmethod
    def _create_extra_email() -> MemberExtraEmail:
        return MemberExtraEmailFactory.create(
            email="extra@example.com", confirmed_on=timezone.now()
        )

    def _post(self, categories_registered_to: dict[str, bool]):
        return self.client.post(
            reverse("core:subscription_management_extra_categories"),
            data={
                "token": "the_token",
                "categories_registered_to": categories_registered_to,
            },
            content_type="application/json",
        )
