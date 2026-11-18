from unittest.mock import patch, MagicMock

from tapir.accounts.exceptions import VerificationEmailsAlreadySendingException
from tapir.accounts.models import TapirUser
from tapir.accounts.services.unverified_members_service import (
    UnverifiedMembersService,
)
from tapir.accounts.tasks import send_verification_emails
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(UnverifiedMembersService, "send_report", autospec=True)
@patch.object(
    UnverifiedMembersService,
    "send_verification_emails",
    autospec=True,
    return_value=[],
)
class TestSendVerificationEmails(TapirIntegrationTest):
    def test_sendVerificationEmails_default_sendsMailsAndReportsToActor(
        self, mock_send_verification_emails: MagicMock, mock_send_report: MagicMock
    ):
        actor = TapirUser.objects.get(id=MemberFactory.create().id)
        members = MemberFactory.create_batch(2)
        failures = [(members[0], "failed")]
        mock_send_verification_emails.return_value = failures

        send_verification_emails(
            member_ids=[member.id for member in members], actor_id=actor.id
        )

        mock_send_verification_emails.assert_called_once_with(
            members=members, actor=actor
        )
        mock_send_report.assert_called_once_with(
            recipient=actor, member_count=2, failures=failures, cache={}
        )

    def test_sendVerificationEmails_alreadySending_sendsNoReport(
        self, mock_send_verification_emails: MagicMock, mock_send_report: MagicMock
    ):
        actor = MemberFactory.create()
        mock_send_verification_emails.side_effect = (
            VerificationEmailsAlreadySendingException()
        )

        send_verification_emails(
            member_ids=[MemberFactory.create().id], actor_id=actor.id
        )

        mock_send_report.assert_not_called()
