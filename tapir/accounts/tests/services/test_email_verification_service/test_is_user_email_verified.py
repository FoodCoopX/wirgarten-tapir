from unittest.mock import patch, MagicMock

from tapir.accounts.services.email_verification_service import EmailVerificationService
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestEmailVerificationService(TapirUnitTest):
    @patch.object(KeycloakUserManager, "get_keycloak_client", autospec=True)
    def test_isUserEmailVerified_emailIsVerified_returnsTrue(
        self, mock_get_keycloak_client: MagicMock
    ):
        mock_client = MagicMock()
        mock_get_keycloak_client.return_value = mock_client
        mock_user_data_from_keycloak = {"emailVerified": True}
        mock_client.get_user.return_value = mock_user_data_from_keycloak
        user = MemberFactory.build(keycloak_id="1234")
        cache = MagicMock()

        self.assertTrue(
            EmailVerificationService.is_user_email_verified(user=user, cache=cache)
        )

        mock_get_keycloak_client.assert_called_once_with(cache=cache)
        mock_client.get_user.assert_called_once_with("1234")

    @patch.object(KeycloakUserManager, "get_keycloak_client", autospec=True)
    def test_isUserEmailVerified_emailIsNotVerified_returnsFalse(
        self, mock_get_keycloak_client: MagicMock
    ):
        mock_client = MagicMock()
        mock_get_keycloak_client.return_value = mock_client
        mock_user_data_from_keycloak = {"emailVerified": False}
        mock_client.get_user.return_value = mock_user_data_from_keycloak
        user = MemberFactory.build(keycloak_id="1234")
        cache = MagicMock()

        self.assertFalse(
            EmailVerificationService.is_user_email_verified(user=user, cache=cache)
        )

        mock_get_keycloak_client.assert_called_once_with(cache=cache)
        mock_client.get_user.assert_called_once_with("1234")

    @patch.object(KeycloakUserManager, "get_keycloak_client", autospec=True)
    def test_isUserEmailVerified_keycloakRaisesAnError_returnsFalse(
        self, mock_get_keycloak_client: MagicMock
    ):
        mock_client = MagicMock()
        mock_get_keycloak_client.return_value = mock_client
        mock_client.get_user.side_effect = Exception()
        user = MemberFactory.build(keycloak_id="1234")
        cache = MagicMock()

        self.assertFalse(
            EmailVerificationService.is_user_email_verified(user=user, cache=cache)
        )

        mock_get_keycloak_client.assert_called_once_with(cache=cache)
        mock_client.get_user.assert_called_once_with("1234")
