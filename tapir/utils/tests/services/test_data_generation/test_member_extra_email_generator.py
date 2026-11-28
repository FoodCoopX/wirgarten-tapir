import datetime
from unittest.mock import ANY, MagicMock, call, patch

import factory.random

from tapir.core.services.member_extra_email_registration_snapshotter import (
    MemberExtraEmailRegistrationSnapshotter,
)
from tapir.utils.services.test_data_generation.member_extra_email_generator import (
    MemberExtraEmailGenerator,
)
from tapir.wirgarten.models import MemberExtraEmail
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestMemberExtraEmailGenerator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(MemberExtraEmailGenerator, "EXTRA_EMAIL_PROBABILITY", 1)
    @patch.object(MemberExtraEmailRegistrationSnapshotter, "snapshot", autospec=True)
    def test_generateMemberExtraEmails_default_snapshotsOnlyConfirmedExtrasWithDirectMails(
        self, mock_snapshot: MagicMock
    ):
        now = mock_timezone(test=self, now=datetime.datetime(year=2026, month=6, day=1))
        factory.random.reseed_random("tapir")
        members = MemberFactory.create_batch(size=60)

        MemberExtraEmailGenerator.generate_member_extra_emails()

        extra_emails = list(MemberExtraEmail.objects.order_by("member__email"))
        self.assertEqual(
            sorted(member.id for member in members),
            sorted(extra_email.member_id for extra_email in extra_emails),
        )
        self.assertEqual(
            {(False, False), (False, True), (True, False), (True, True)},
            {
                (extra_email.is_confirmed, extra_email.receives_direct_mails)
                for extra_email in extra_emails
            },
        )
        for extra_email in extra_emails:
            self.assertEqual(
                f"{extra_email.member.email.split('@')[0]}.extra@example.com",
                extra_email.email,
            )
            self.assertIn(extra_email.confirmed_on, [None, now])
        self.assertEqual(
            [
                call(extra_email=extra_email, cache=ANY)
                for extra_email in extra_emails
                if extra_email.is_confirmed and extra_email.receives_direct_mails
            ],
            mock_snapshot.call_args_list,
        )
