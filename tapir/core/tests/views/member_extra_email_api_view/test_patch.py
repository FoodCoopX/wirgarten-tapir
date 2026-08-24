from django.urls import reverse
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import (
    MemberExtraEmailUpdatedLogEntry,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberExtraEmailApiViewPatch(TapirIntegrationTest):
    maxDiff = 3000

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=True)

    def test_patch_featureIsDisabled_returns400(self):
        self.client.force_login(MemberFactory.create())
        TapirParameter.objects.filter(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES
        ).update(value=False)

        response = self.client.patch(reverse("core:member_extra_emails"))

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_patch_default_updatesNamesAndCreatesLogEntry(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        extra_email = MemberExtraEmailFactory.create(
            member=member, first_name="before_first", last_name="before_last"
        )

        url = reverse("core:member_extra_emails")
        response = self.client.patch(
            url,
            data={
                "extra_email_id": extra_email.id,
                "first_name": "after_first",
                "last_name": "after_last",
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        extra_email.refresh_from_db()
        self.assertEqual("after_first", extra_email.first_name)
        self.assertEqual("after_last", extra_email.last_name)

        self.assertEqual(1, MemberExtraEmailUpdatedLogEntry.objects.count())
        log_entry = MemberExtraEmailUpdatedLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.actor.email)
        self.assertEqual(member.email, log_entry.user.email)

    def test_patch_adminCreatesExtraMailForAnotherMember_updatesNamesAndCreatesLogEntry(
        self,
    ):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        extra_email = MemberExtraEmailFactory.create(
            first_name="before_first", last_name="before_last"
        )

        url = reverse("core:member_extra_emails")
        response = self.client.patch(
            url,
            data={
                "extra_email_id": extra_email.id,
                "first_name": "after_first",
                "last_name": "after_last",
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        extra_email.refresh_from_db()
        self.assertEqual("after_first", extra_email.first_name)
        self.assertEqual("after_last", extra_email.last_name)

        self.assertEqual(1, MemberExtraEmailUpdatedLogEntry.objects.count())
        log_entry = MemberExtraEmailUpdatedLogEntry.objects.get()
        self.assertEqual(admin.email, log_entry.actor.email)
        self.assertEqual(extra_email.member.email, log_entry.user.email)

    def test_patch_normalMemberUpdatesExtraMailForAnotherMember_returns403(self):
        logged_in_user = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_user)
        extra_email = MemberExtraEmailFactory.create(
            first_name="before_first", last_name="before_last"
        )

        url = reverse("core:member_extra_emails")
        response = self.client.patch(
            url,
            data={
                "extra_email_id": extra_email.id,
                "first_name": "after_first",
                "last_name": "after_last",
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        extra_email.refresh_from_db()
        self.assertEqual("before_first", extra_email.first_name)
        self.assertEqual("before_last", extra_email.last_name)
        self.assertFalse(MemberExtraEmailUpdatedLogEntry.objects.exists())
