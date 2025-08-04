from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from keycloak import KeycloakOpenIDConnection, KeycloakAdmin

if TYPE_CHECKING:
    pass


class KeycloakUserManager:
    @classmethod
    def get_keycloak_client(cls):
        config = settings.KEYCLOAK_ADMIN_CONFIG

        keycloak_connection = KeycloakOpenIDConnection(
            server_url=config["SERVER_URL"],
            realm_name=config["REALM_NAME"],
            client_id=config["CLIENT_ID"],
            client_secret_key=config["CLIENT_SECRET_KEY"],
            verify=True,
        )

        return KeycloakAdmin(connection=keycloak_connection)

    @classmethod
    def get_user_roles(cls, keycloak_id):
        keycloak_client = KeycloakUserManager.get_keycloak_client()

        raw_roles = keycloak_client.get_composite_realm_roles_of_user(
            keycloak_id,
        )

        return [
            raw_role["name"]
            for raw_role in raw_roles
            if raw_role["name"] not in settings.KEYCLOAK_NON_TAPIR_ROLES
        ]
