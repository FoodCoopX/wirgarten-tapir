from unittest.mock import ANY, MagicMock, patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.core.services.member_extra_email_registration_snapshotter import (
    MemberExtraEmailRegistrationSnapshotter,
)
from tapir.wirgarten.models import MemberExtraEmail, MemberExtraEmailConfirmedLogEntry
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(MemberExtraEmailRegistrationSnapshotter, "snapshot", autospec=True)
class TestConfirmMemberExtraEmailApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=True)

    def test_get_featureIsDisabled_returns400(self, _: MagicMock):
        self.client.force_login(MemberFactory.create())
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=False)
        extra_email = MemberExtraEmail.objects.create(
            member=MemberFactory.create(), email="test@example.com"
        )

        response = self.client.get(
            reverse(
                "core:member_extra_email_confirm", kwargs={"secret": extra_email.secret}
            )
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_default_confirmRecipientAndCreatesLogEntry(
        self, mock_snapshot: MagicMock
    ):
        member = MemberFactory.create()
        extra_email = MemberExtraEmail.objects.create(
            member=member, email="test@example.com"
        )
        self.client.logout()

        self.assertIsNone(extra_email.confirmed_on)

        url = reverse(
            "core:member_extra_email_confirm", kwargs={"secret": extra_email.secret}
        )
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_302_FOUND)
        self.assertRedirects(
            response,
            expected_url=reverse(
                "core:member_extra_email_confirmed",
                kwargs={"secret": extra_email.secret},
            ),
        )

        extra_email.refresh_from_db()
        self.assertIsNotNone(extra_email.confirmed_on)

        self.assertEqual(1, MemberExtraEmailConfirmedLogEntry.objects.count())
        log_entry = MemberExtraEmailConfirmedLogEntry.objects.get()
        self.assertEqual("test@example.com", log_entry.email)
        self.assertIsNone(log_entry.actor)
        self.assertEqual(member.email, log_entry.user.email)
        mock_snapshot.assert_called_once_with(extra_email=extra_email, cache=ANY)

    def test_get_extraDoesNotReceiveDirectMails_doesNotSnapshot(
        self, mock_snapshot: MagicMock
    ):
        extra_email = MemberExtraEmail.objects.create(
            member=MemberFactory.create(),
            email="test@example.com",
            receives_direct_mails=False,
        )

        response = self.client.get(self._build_url(extra_email=extra_email))

        self.assertStatusCode(response, status.HTTP_302_FOUND)
        extra_email.refresh_from_db()
        self.assertIsNotNone(extra_email.confirmed_on)
        mock_snapshot.assert_not_called()

    def test_get_extraIsAlreadyConfirmed_doesNotSnapshotAgain(
        self, mock_snapshot: MagicMock
    ):
        extra_email = MemberExtraEmail.objects.create(
            member=MemberFactory.create(),
            email="test@example.com",
            confirmed_on=timezone.now(),
        )

        response = self.client.get(self._build_url(extra_email=extra_email))

        self.assertStatusCode(response, status.HTTP_302_FOUND)
        mock_snapshot.assert_not_called()

    @staticmethod
    def _build_url(extra_email: MemberExtraEmail) -> str:
        return reverse(
            "core:member_extra_email_confirm", kwargs={"secret": extra_email.secret}
        )
