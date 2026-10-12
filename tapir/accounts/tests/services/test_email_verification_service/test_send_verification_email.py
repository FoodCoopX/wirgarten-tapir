from unittest.mock import patch, MagicMock

from django.test import override_settings

from tapir.accounts.services.email_verification_service import EmailVerificationService
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.log.models import TextLogEntry
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestSendVerificationEmail(TapirIntegrationTest):
    @override_settings(
        SITE_URL="TEST_REDIRECT",
        KEYCLOAK_ADMIN_CONFIG={"FRONTEND_CLIENT_ID": "TEST_CLIENT_ID"},
        KEYCLOAK_SKIP_VERIFICATION_EMAIL=False,
    )
    @patch.object(KeycloakUserManager, "get_keycloak_client")
    def test_sendVerificationEmail_default_sendsExecuteActionsMailWithVerifyEmailAndCreatesLogEntry(
        self, mock_get_keycloak_client: MagicMock
    ):
        mock_client = MagicMock()
        mock_get_keycloak_client.return_value = mock_client
        user = MemberFactory.create(keycloak_id="1234")
        actor = MemberFactory.create()
        cache = MagicMock()

        EmailVerificationService.send_verification_email(
            user=user, actor=actor, cache=cache
        )

        mock_get_keycloak_client.assert_called_once_with(cache=cache)
        mock_client.send_update_account.assert_called_once_with(
            user_id="1234",
            payload=["VERIFY_EMAIL"],
            redirect_uri="TEST_REDIRECT",
            client_id="TEST_CLIENT_ID",
        )
        mock_client.send_verify_email.assert_not_called()

        self.assertEqual(1, TextLogEntry.objects.count())
        log_entry = TextLogEntry.objects.get()
        self.assertEqual(
            'Keycloak Email gesendet: "Aktivierung des Benutzerkontos"', log_entry.text
        )
        self.assertEqual(user.email, log_entry.user.email)
        self.assertEqual(actor.email, log_entry.actor.email)

    @override_settings(
        SITE_URL="TEST_REDIRECT",
        KEYCLOAK_ADMIN_CONFIG={"FRONTEND_CLIENT_ID": "TEST_CLIENT_ID"},
        KEYCLOAK_SKIP_VERIFICATION_EMAIL=True,
    )
    @patch.object(KeycloakUserManager, "get_keycloak_client")
    def test_sendVerificationEmail_skipVerificationEnabled_onlyCreateLogEntry(
        self, mock_get_keycloak_client: MagicMock
    ):
        mock_client = MagicMock()
        mock_get_keycloak_client.return_value = mock_client
        user = MemberFactory.create(keycloak_id="1234")
        actor = MemberFactory.create()
        cache = MagicMock()

        EmailVerificationService.send_verification_email(
            user=user, actor=actor, cache=cache
        )

        mock_get_keycloak_client.assert_not_called()
        mock_client.send_verify_email.assert_not_called()
        mock_client.send_update_account.assert_not_called()

        self.assertEqual(1, TextLogEntry.objects.count())
        log_entry = TextLogEntry.objects.get()
        self.assertEqual(
            'Keycloak Email gesendet: "Aktivierung des Benutzerkontos"', log_entry.text
        )
        self.assertEqual(user.email, log_entry.user.email)
        self.assertEqual(actor.email, log_entry.actor.email)
