from unittest.mock import ANY, MagicMock, patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.core.services.mailman.mailing_list_unsubscriber import (
    MailingListUnsubscriber,
)
from tapir.wirgarten.models import MemberExtraEmail, MemberExtraEmailDeletedLogEntry
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(MailingListUnsubscriber, "unsubscribe_if_address_unused", autospec=True)
class TestMemberExtraEmailApiViewDelete(TapirIntegrationTest):
    maxDiff = 3000

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=True)

    def test_delete_featureIsDisabled_returns403(self, _: MagicMock):
        self.client.force_login(MemberFactory.create())
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=False)

        response = self.client.delete(reverse("core:member_extra_emails"))

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_delete_default_extraEmailIsDeletedAndLogEntryCreated(self, _: MagicMock):
        member = MemberFactory.create()
        self.client.force_login(member)

        extra_email = MemberExtraEmail.objects.create(
            member=member, email="test@example.com"
        )

        url = reverse("core:member_extra_emails")
        url = f"{url}?extra_email_id={extra_email.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertFalse(MemberExtraEmail.objects.exists())

        self.assertEqual(1, MemberExtraEmailDeletedLogEntry.objects.count())
        log_entry = MemberExtraEmailDeletedLogEntry.objects.get()
        self.assertEqual("test@example.com", log_entry.email)
        self.assertEqual(member.email, log_entry.actor.email)
        self.assertEqual(member.email, log_entry.user.email)

    def test_delete_adminDeletesMailFromAnotherMember_extraEmailIsDeletedAndLogEntryCreated(
        self, _: MagicMock
    ):
        admin = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(admin)

        extra_email = MemberExtraEmail.objects.create(
            member=other_member, email="test@example.com"
        )

        url = reverse("core:member_extra_emails")
        url = f"{url}?extra_email_id={extra_email.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertFalse(MemberExtraEmail.objects.exists())

        self.assertEqual(1, MemberExtraEmailDeletedLogEntry.objects.count())
        log_entry = MemberExtraEmailDeletedLogEntry.objects.get()
        self.assertEqual("test@example.com", log_entry.email)
        self.assertEqual(admin.email, log_entry.actor.email)
        self.assertEqual(other_member.email, log_entry.user.email)

    def test_delete_normalMemberDeletesMailFromAnotherMember_returns403(
        self, _: MagicMock
    ):
        admin = MemberFactory.create(is_superuser=False)
        other_member = MemberFactory.create()
        self.client.force_login(admin)

        extra_email = MemberExtraEmail.objects.create(
            member=other_member, email="test@example.com"
        )

        url = reverse("core:member_extra_emails")
        url = f"{url}?extra_email_id={extra_email.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertEqual(1, MemberExtraEmail.objects.count())
        self.assertFalse(MemberExtraEmailDeletedLogEntry.objects.exists())

    def test_delete_confirmedExtraEmail_unsubscribesFromAllListsAfterCommit(
        self, mock_unsubscribe_if_address_unused: MagicMock
    ):
        member = MemberFactory.create()
        self.client.force_login(member)
        extra_email = MemberExtraEmail.objects.create(
            member=member, email="test@example.com", confirmed_on=timezone.now()
        )

        url = reverse("core:member_extra_emails")
        url = f"{url}?extra_email_id={extra_email.id}"
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        mock_unsubscribe_if_address_unused.assert_called_once_with(
            email="test@example.com", cache=ANY
        )

    def test_delete_unconfirmedExtraEmail_doesNotUnsubscribe(
        self, mock_unsubscribe_if_address_unused: MagicMock
    ):
        member = MemberFactory.create()
        self.client.force_login(member)
        extra_email = MemberExtraEmail.objects.create(
            member=member, email="test@example.com"
        )

        url = reverse("core:member_extra_emails")
        url = f"{url}?extra_email_id={extra_email.id}"
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        mock_unsubscribe_if_address_unused.assert_not_called()
