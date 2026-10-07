from unittest.mock import patch, MagicMock

from keycloak import KeycloakDeleteError

from tapir.accounts.services.keycloak_user_delete_service import (
    KeycloakUserDeleteService,
)
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestKeycloakUserDeleteService(TapirUnitTest):
    @patch.object(KeycloakUserManager, "get_keycloak_client", autospec=True)
    def test_deleteUserIfExists_userHasNoKeycloakId_doNothing(
        self, mock_get_keycloak_client: MagicMock
    ):
        mock_client = MagicMock()
        mock_get_keycloak_client.return_value = mock_client
        user = MemberFactory.build(keycloak_id="")

        KeycloakUserDeleteService.delete_user_if_exists(user=user, cache=MagicMock())

        mock_get_keycloak_client.assert_not_called()
        mock_client.delete_user.assert_not_called()

    @patch.object(KeycloakUserManager, "get_keycloak_client", autospec=True)
    def test_deleteUserIfExists_default_deletesUser(
        self, mock_get_keycloak_client: MagicMock
    ):
        mock_client = MagicMock()
        mock_get_keycloak_client.return_value = mock_client
        user = MemberFactory.build(keycloak_id="1234")
        cache = MagicMock()

        KeycloakUserDeleteService.delete_user_if_exists(user=user, cache=cache)

        mock_get_keycloak_client.assert_called_once_with(cache)
        mock_client.delete_user.assert_called_once_with("1234")

    @patch.object(KeycloakUserManager, "get_keycloak_client", autospec=True)
    def test_deleteUserIfExists_userNotFoundOnKeycloak_noErrorRaised(
        self, mock_get_keycloak_client: MagicMock
    ):
        mock_client = MagicMock()
        mock_client.delete_user.side_effect = KeycloakDeleteError(
            error_message=b'{"error":"User not found"}'
        )
        mock_get_keycloak_client.return_value = mock_client
        user = MemberFactory.build(keycloak_id="1234")
        cache = MagicMock()

        KeycloakUserDeleteService.delete_user_if_exists(user=user, cache=cache)

        mock_get_keycloak_client.assert_called_once_with(cache)
        mock_client.delete_user.assert_called_once_with("1234")

    @patch.object(KeycloakUserManager, "get_keycloak_client", autospec=True)
    def test_deleteUserIfExists_otherKeycloakError_errorRaised(
        self, mock_get_keycloak_client: MagicMock
    ):
        mock_client = MagicMock()
        mock_client.delete_user.side_effect = KeycloakDeleteError(
            error_message=b'{"error":"Other error"}'
        )
        mock_get_keycloak_client.return_value = mock_client
        user = MemberFactory.build(keycloak_id="1234")
        cache = MagicMock()

        with self.assertRaises(KeycloakDeleteError):
            KeycloakUserDeleteService.delete_user_if_exists(user=user, cache=cache)

        mock_get_keycloak_client.assert_called_once_with(cache)
        mock_client.delete_user.assert_called_once_with("1234")
