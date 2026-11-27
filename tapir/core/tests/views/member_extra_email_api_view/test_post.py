from unittest.mock import patch, Mock

from django.conf import settings
from django.urls import reverse
from rest_framework import status
from tapir.mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import MemberExtraEmail, MemberExtraEmailCreatedLogEntry
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberExtraEmailApiViewPost(TapirIntegrationTest):
    maxDiff = 3000

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=True)

    def test_post_featureIsDisabled_returns400(self):
        self.client.force_login(MemberFactory.create())
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=False)

        response = self.client.post(reverse("core:member_extra_emails"))

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_default_createsUnconfirmedRecipientAndCreatesLogEntryAndFireTrigger(
        self, mock_fire_action: Mock
    ):
        member = MemberFactory.create()
        self.client.force_login(member)

        url = reverse("core:member_extra_emails")
        response = self.client.post(
            url,
            data={
                "extra_email": "test@example.com",
                "member_id": member.id,
                "first_name": "test_first",
                "last_name": "test_last",
                "receives_direct_mails": False,
            },
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, MemberExtraEmail.objects.count())
        extra_email = MemberExtraEmail.objects.get()
        self.assertEqual("test@example.com", extra_email.email)
        self.assertEqual(member, extra_email.member)
        self.assertIsNone(extra_email.confirmed_on)
        self.assertFalse(extra_email.receives_direct_mails)

        self.assertEqual(1, MemberExtraEmailCreatedLogEntry.objects.count())
        log_entry = MemberExtraEmailCreatedLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.actor.email)
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual("test@example.com", log_entry.email)

        confirmation_link = f"{settings.SITE_URL}{reverse("core:member_extra_email_confirm", kwargs={"secret": extra_email.secret})}"
        mock_fire_action.assert_called_once_with(
            TransactionalTriggerData(
                key=Events.EXTRA_MAIL_CONFIRMATION,
                token_data={
                    "confirmation_link": confirmation_link,
                    "main_mail_address": member.email,
                },
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email="test@example.com",
                    first_name=member.first_name,
                    last_name=member.last_name,
                ),
            )
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_adminCreatesExtraMailForAnotherMember_createsRecipient(
        self, mock_fire_action: Mock
    ):
        admin = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(admin)

        url = reverse("core:member_extra_emails")
        response = self.client.post(
            url,
            data={
                "extra_email": "test@example.com",
                "member_id": other_member.id,
                "first_name": "test_first",
                "last_name": "test_last",
                "receives_direct_mails": False,
            },
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, MemberExtraEmail.objects.count())
        extra_email = MemberExtraEmail.objects.get()
        self.assertEqual("test@example.com", extra_email.email)
        self.assertEqual(other_member, extra_email.member)
        self.assertEqual("test_first", extra_email.first_name)
        self.assertEqual("test_last", extra_email.last_name)
        self.assertFalse(extra_email.receives_direct_mails)

        self.assertEqual(1, MemberExtraEmailCreatedLogEntry.objects.count())
        log_entry = MemberExtraEmailCreatedLogEntry.objects.get()
        self.assertEqual(admin.email, log_entry.actor.email)
        self.assertEqual(other_member.email, log_entry.user.email)
        self.assertEqual("test@example.com", log_entry.email)

        confirmation_link = f"{settings.SITE_URL}{reverse("core:member_extra_email_confirm", kwargs={"secret": extra_email.secret})}"
        mock_fire_action.assert_called_once_with(
            TransactionalTriggerData(
                key=Events.EXTRA_MAIL_CONFIRMATION,
                token_data={
                    "confirmation_link": confirmation_link,
                    "main_mail_address": other_member.email,
                },
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email="test@example.com",
                    first_name=other_member.first_name,
                    last_name=other_member.last_name,
                ),
            )
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_normalMemberCreatesExtraMailForAnotherMember_returns403(
        self, mock_fire_action: Mock
    ):
        admin = MemberFactory.create(is_superuser=False)
        other_member = MemberFactory.create()
        self.client.force_login(admin)

        url = reverse("core:member_extra_emails")
        response = self.client.post(
            url,
            data={
                "extra_email": "test@example.com",
                "member_id": other_member.id,
                "first_name": "test_first",
                "last_name": "test_last",
                "receives_direct_mails": False,
            },
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertFalse(MemberExtraEmail.objects.exists())
        self.assertFalse(MemberExtraEmailCreatedLogEntry.objects.exists())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_emailIsInvalid_returns400(self, mock_fire_action: Mock):
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self._post_extra_email(member_id=member.id, extra_email="invalid")

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            {"extra_email": ["Gib eine gültige E-Mail Adresse an."]}, response.json()
        )
        self.assertFalse(MemberExtraEmail.objects.exists())
        self.assertFalse(MemberExtraEmailCreatedLogEntry.objects.exists())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_emailAlreadyExists_returns400(self, mock_fire_action: Mock):
        member = MemberFactory.create()
        self.client.force_login(member)

        MemberExtraEmail.objects.create(member=member, email="test@example.com")

        response = self._post_extra_email(
            member_id=member.id, extra_email="test@example.com"
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            ["Diese zusätzliche Adresse existiert bereits"], response.json()
        )
        self.assertEqual(1, MemberExtraEmail.objects.count())
        self.assertFalse(MemberExtraEmailCreatedLogEntry.objects.exists())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_emailIsTheOwnMainAddress_returns400(self, mock_fire_action: Mock):
        member = MemberFactory.create(email="main@example.com")
        self.client.force_login(member)

        response = self._post_extra_email(
            member_id=member.id, extra_email=" Main@Example.com"
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            ["Diese Adresse ist bereits die Hauptadresse des Mitglieds"],
            response.json(),
        )
        self.assertFalse(MemberExtraEmail.objects.exists())
        self.assertFalse(MemberExtraEmailCreatedLogEntry.objects.exists())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_mixedCaseAddress_storesTheNormalisedAddress(self, _: Mock):
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self._post_extra_email(
            member_id=member.id, extra_email=" Extra@Example.com"
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("extra@example.com", MemberExtraEmail.objects.get().email)

    def _post_extra_email(self, member_id: str, extra_email: str):
        return self.client.post(
            reverse("core:member_extra_emails"),
            data={
                "extra_email": extra_email,
                "member_id": member_id,
                "first_name": "test_first",
                "last_name": "test_last",
                "receives_direct_mails": True,
            },
        )
