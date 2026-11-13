from unittest.mock import patch, MagicMock, call

from tapir.accounts.exceptions import VerificationEmailsAlreadySendingException
from tapir.accounts.services.email_verification_service import (
    EmailVerificationService,
)
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.accounts.services.unverified_members_service import (
    UnverifiedMembersService,
)
from tapir.log.models import TextLogEntry
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(UnverifiedMembersService, "_build_lock", autospec=True)
@patch("tapir.accounts.services.unverified_members_service.time.sleep", autospec=True)
@patch.object(EmailVerificationService, "send_verification_email", autospec=True)
@patch.object(KeycloakUserManager, "create_keycloak_user_if_necessary", autospec=True)
class TestSendVerificationEmails(TapirIntegrationTest):
    def test_sendVerificationEmails_default_createsAccountsAndSendsMailsWithPause(
        self,
        mock_create_keycloak_user: MagicMock,
        mock_send_verification_email: MagicMock,
        mock_sleep: MagicMock,
        _: MagicMock,
    ):
        members = MemberFactory.build_batch(2)
        actor = MemberFactory.build()

        UnverifiedMembersService.send_verification_emails(members=members, actor=actor)

        self.assertEqual(
            [call(user=member, initial_password=None) for member in members],
            mock_create_keycloak_user.call_args_list,
        )
        self.assertEqual(
            [call(user=member, actor=actor) for member in members],
            mock_send_verification_email.call_args_list,
        )
        mock_sleep.assert_called_once_with(
            UnverifiedMembersService.SECONDS_BETWEEN_MAILS
        )

    def test_sendVerificationEmails_oneMailFails_continuesAndReturnsAndLogsFailure(
        self,
        _: MagicMock,
        mock_send_verification_email: MagicMock,
        __: MagicMock,
        ___: MagicMock,
    ):
        members = MemberFactory.create_batch(2)
        actor = MemberFactory.create()
        mock_send_verification_email.side_effect = [Exception("failed"), None]

        failures = UnverifiedMembersService.send_verification_emails(
            members=members, actor=actor
        )

        self.assertEqual(2, mock_send_verification_email.call_count)
        self.assertEqual([(members[0], "failed")], failures)
        log_entry = TextLogEntry.objects.get()
        self.assertEqual(members[0].id, log_entry.user_id)
        self.assertEqual(actor.id, log_entry.actor_id)
        self.assertIn("failed", log_entry.text)

    def test_sendVerificationEmails_default_releasesLockWithTimeoutBasedOnEstimate(
        self, _: MagicMock, __: MagicMock, ___: MagicMock, mock_build_lock: MagicMock
    ):
        members = MemberFactory.build_batch(2)

        UnverifiedMembersService.send_verification_emails(members=members, actor=None)

        mock_build_lock.assert_called_once_with(
            timeout=2 * UnverifiedMembersService.SECONDS_BETWEEN_MAILS
            + UnverifiedMembersService.LOCK_TIMEOUT_MARGIN_SECONDS
        )
        mock_build_lock.return_value.acquire.assert_called_once_with(blocking=False)
        mock_build_lock.return_value.release.assert_called_once_with()

    def test_sendVerificationEmails_lockAlreadyHeld_raisesErrorAndSendsNothing(
        self,
        mock_create_keycloak_user: MagicMock,
        mock_send_verification_email: MagicMock,
        _: MagicMock,
        mock_build_lock: MagicMock,
    ):
        mock_build_lock.return_value.acquire.return_value = False

        with self.assertRaises(VerificationEmailsAlreadySendingException):
            UnverifiedMembersService.send_verification_emails(
                members=MemberFactory.build_batch(2), actor=None
            )

        mock_create_keycloak_user.assert_not_called()
        mock_send_verification_email.assert_not_called()
        mock_build_lock.return_value.release.assert_not_called()
