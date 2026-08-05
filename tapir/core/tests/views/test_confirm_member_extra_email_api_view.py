from django.urls import reverse
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import MemberExtraEmail, MemberExtraEmailConfirmedLogEntry
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestConfirmMemberExtraEmailApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=True)

    def test_get_featureIsDisabled_returns400(self):
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

    def test_get_default_confirmRecipientAndCreatesLogEntry(self):
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
