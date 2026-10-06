from keycloak import KeycloakDeleteError

from tapir.accounts.models import KeycloakUser
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager


class KeycloakUserDeleteService:
    @classmethod
    def delete_user_if_exists(cls, user: KeycloakUser, cache: dict):
        if not user.keycloak_id:
            return
        client = KeycloakUserManager.get_keycloak_client(cache)
        try:
            client.delete_user(user.keycloak_id)
        except KeycloakDeleteError as error:
            if error.error_message == b'{"error":"User not found"}':
                return
            raise
