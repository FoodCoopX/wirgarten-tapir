from unittest.mock import ANY, MagicMock, patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from tapir.core.services.mailman.mailing_list_unsubscriber import (
    MailingListUnsubscriber,
)
from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.wirgarten.models import MemberExtraEmail, MemberExtraEmailDeletedLogEntry
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(MailingListUnsubscriber, "unsubscribe_if_address_unused", autospec=True)
@patch.object(
    SubscriptionManagementTokenSigner,
    "get_address",
    autospec=True,
    return_value="extra@example.com",
)
class TestSubscriptionManagementExtraApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)

    def test_delete_tokenIsInvalid_returns403(
        self, mock_get_address: MagicMock, mock_unsubscribe_if_address_unused: MagicMock
    ):
        mock_get_address.return_value = None
        MemberExtraEmailFactory.create(
            email="extra@example.com", confirmed_on=timezone.now()
        )

        response = self._delete()

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertTrue(MemberExtraEmail.objects.exists())
        mock_unsubscribe_if_address_unused.assert_not_called()

    def test_delete_featureDisabled_returns400(
        self, _: MagicMock, mock_unsubscribe_if_address_unused: MagicMock
    ):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=False)
        MemberExtraEmailFactory.create(
            email="extra@example.com", confirmed_on=timezone.now()
        )

        response = self._delete()

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(MemberExtraEmail.objects.exists())
        mock_unsubscribe_if_address_unused.assert_not_called()

    def test_delete_confirmedExtra_deletesTheExtraAndLogsTheDeletionWithoutActorAndUnsubscribesAfterCommit(
        self, _: MagicMock, mock_unsubscribe_if_address_unused: MagicMock
    ):
        extra_email = MemberExtraEmailFactory.create(
            email="extra@example.com", confirmed_on=timezone.now()
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self._delete()

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertFalse(MemberExtraEmail.objects.exists())
        log_entry = MemberExtraEmailDeletedLogEntry.objects.get()
        self.assertEqual("extra@example.com", log_entry.email)
        self.assertEqual(extra_email.member_id, log_entry.user_id)
        self.assertIsNone(log_entry.actor)
        mock_unsubscribe_if_address_unused.assert_called_once_with(
            email="extra@example.com", cache=ANY
        )

    def _delete(self):
        return self.client.delete(
            reverse("core:subscription_management_extra") + "?token=the_token"
        )
