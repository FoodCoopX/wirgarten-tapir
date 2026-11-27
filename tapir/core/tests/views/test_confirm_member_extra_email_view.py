import datetime
from unittest.mock import ANY, MagicMock, patch

from django.http import HttpResponse
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
class TestConfirmMemberExtraEmailView(TapirIntegrationTest):
    MAIN_ADDRESS_MESSAGE = "Diese Adresse ist bereits die Hauptadresse eines Mitglieds"
    OTHER_MEMBER_MESSAGE = "Diese Adresse ist bereits als zusätzliche Adresse eines anderen Mitglieds bestätigt"

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=True)

    def test_get_featureIsDisabled_returns403(self, _: MagicMock):
        self._disable_feature()
        extra_email = self._create_extra_email()

        response = self.client.get(self._build_url(extra_email=extra_email))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_unconfirmedExtra_showsTheConfirmationPageWithoutConfirming(
        self, mock_snapshot: MagicMock
    ):
        extra_email = self._create_extra_email()

        response = self.client.get(self._build_url(extra_email=extra_email))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "core/member_extra_email_confirm.html")
        self._assert_not_confirmed(extra_email=extra_email, mock_snapshot=mock_snapshot)

    def test_get_extraIsAlreadyConfirmed_redirectsToTheConfirmedPage(
        self, _: MagicMock
    ):
        extra_email = self._create_extra_email(confirmed_on=timezone.now())

        response = self.client.get(self._build_url(extra_email=extra_email))

        self._assert_redirects_to_confirmed_page(
            response=response, extra_email=extra_email
        )

    def test_get_addressIsAMainAddress_showsTheRefusal(self, mock_snapshot: MagicMock):
        MemberFactory.create(email="main@example.com")
        extra_email = self._create_extra_email(email="main@example.com")

        response = self.client.get(self._build_url(extra_email=extra_email))

        self._assert_refused(
            response=response,
            message=self.MAIN_ADDRESS_MESSAGE,
            extra_email=extra_email,
            mock_snapshot=mock_snapshot,
        )

    def test_post_featureIsDisabled_returns403(self, mock_snapshot: MagicMock):
        self._disable_feature()
        extra_email = self._create_extra_email()

        response = self.client.post(self._build_url(extra_email=extra_email))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self._assert_not_confirmed(extra_email=extra_email, mock_snapshot=mock_snapshot)

    def test_post_default_confirmsSnapshotsAndCreatesLogEntry(
        self, mock_snapshot: MagicMock
    ):
        extra_email = self._create_extra_email()
        self.client.logout()

        response = self.client.post(self._build_url(extra_email=extra_email))

        self._assert_redirects_to_confirmed_page(
            response=response, extra_email=extra_email
        )
        extra_email.refresh_from_db()
        self.assertIsNotNone(extra_email.confirmed_on)
        log_entry = MemberExtraEmailConfirmedLogEntry.objects.get()
        self.assertEqual("extra@example.com", log_entry.email)
        self.assertIsNone(log_entry.actor)
        self.assertEqual(extra_email.member_id, log_entry.user_id)
        mock_snapshot.assert_called_once_with(extra_email=extra_email, cache=ANY)

    def test_post_extraDoesNotReceiveDirectMails_confirmsWithoutSnapshot(
        self, mock_snapshot: MagicMock
    ):
        extra_email = self._create_extra_email(receives_direct_mails=False)

        response = self.client.post(self._build_url(extra_email=extra_email))

        self._assert_redirects_to_confirmed_page(
            response=response, extra_email=extra_email
        )
        extra_email.refresh_from_db()
        self.assertIsNotNone(extra_email.confirmed_on)
        mock_snapshot.assert_not_called()

    def test_post_extraIsAlreadyConfirmed_changesNothing(
        self, mock_snapshot: MagicMock
    ):
        confirmed_on = timezone.now()
        extra_email = self._create_extra_email(confirmed_on=confirmed_on)

        response = self.client.post(self._build_url(extra_email=extra_email))

        self._assert_redirects_to_confirmed_page(
            response=response, extra_email=extra_email
        )
        extra_email.refresh_from_db()
        self.assertEqual(confirmed_on, extra_email.confirmed_on)
        self.assertFalse(MemberExtraEmailConfirmedLogEntry.objects.exists())
        mock_snapshot.assert_not_called()

    def test_post_addressIsAMainAddress_refusesConfirmation(
        self, mock_snapshot: MagicMock
    ):
        MemberFactory.create(email="main@example.com")
        extra_email = self._create_extra_email(email="main@example.com")

        response = self.client.post(self._build_url(extra_email=extra_email))

        self._assert_refused(
            response=response,
            message=self.MAIN_ADDRESS_MESSAGE,
            extra_email=extra_email,
            mock_snapshot=mock_snapshot,
        )

    def test_post_addressIsConfirmedForAnotherMember_refusesConfirmation(
        self, mock_snapshot: MagicMock
    ):
        self._create_extra_email(
            email="shared@example.com", confirmed_on=timezone.now()
        )
        extra_email = self._create_extra_email(email="shared@example.com")

        response = self.client.post(self._build_url(extra_email=extra_email))

        self._assert_refused(
            response=response,
            message=self.OTHER_MEMBER_MESSAGE,
            extra_email=extra_email,
            mock_snapshot=mock_snapshot,
        )

    @staticmethod
    def _disable_feature():
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=False)

    @staticmethod
    def _create_extra_email(
        email: str = "extra@example.com",
        confirmed_on: datetime.datetime | None = None,
        receives_direct_mails: bool = True,
    ) -> MemberExtraEmail:
        return MemberExtraEmail.objects.create(
            member=MemberFactory.create(),
            email=email,
            confirmed_on=confirmed_on,
            receives_direct_mails=receives_direct_mails,
        )

    @staticmethod
    def _build_url(extra_email: MemberExtraEmail) -> str:
        return reverse(
            "core:member_extra_email_confirm", kwargs={"secret": extra_email.secret}
        )

    def _assert_redirects_to_confirmed_page(
        self, response: HttpResponse, extra_email: MemberExtraEmail
    ):
        self.assertRedirects(
            response,
            expected_url=reverse(
                "core:member_extra_email_confirmed",
                kwargs={"secret": extra_email.secret},
            ),
        )

    def _assert_refused(
        self,
        response: HttpResponse,
        message: str,
        extra_email: MemberExtraEmail,
        mock_snapshot: MagicMock,
    ):
        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTemplateUsed(
            response, "core/member_extra_email_confirmation_refused.html"
        )
        self.assertContains(response, message)
        self._assert_not_confirmed(extra_email=extra_email, mock_snapshot=mock_snapshot)

    def _assert_not_confirmed(
        self, extra_email: MemberExtraEmail, mock_snapshot: MagicMock
    ):
        extra_email.refresh_from_db()
        self.assertIsNone(extra_email.confirmed_on)
        self.assertFalse(MemberExtraEmailConfirmedLogEntry.objects.exists())
        mock_snapshot.assert_not_called()
