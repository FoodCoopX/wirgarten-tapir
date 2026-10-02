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
    )
    @patch.object(KeycloakUserManager, "get_keycloak_client")
    def test_sendVerificationEmail_default_callKeycloakVerifyAndCreateLogEntry(
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
        mock_client.send_verify_email.assert_called_once_with(
            user_id="1234", redirect_uri="TEST_REDIRECT", client_id="TEST_CLIENT_ID"
        )

        self.assertEqual(1, TextLogEntry.objects.count())
        log_entry = TextLogEntry.objects.get()
        self.assertEqual(
            'Keycloak Email gesendet: "Aktivierung des Benutzerkontos"', log_entry.text
        )
        self.assertEqual(user.email, log_entry.user.email)
        self.assertEqual(actor.email, log_entry.actor.email)
