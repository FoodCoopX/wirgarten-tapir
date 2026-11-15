from __future__ import annotations

import functools

from django.conf import settings
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from keycloak.exceptions import (
    KeycloakAuthenticationError,
    KeycloakConnectionError,
    KeycloakError,
    KeycloakGetError,
)


def build_keycloak_admin(client_id: str, client_secret: str) -> KeycloakAdmin:
    config = settings.KEYCLOAK_ADMIN_CONFIG
    connection = KeycloakOpenIDConnection(
        server_url=config["SERVER_URL"],
        realm_name=config["REALM_NAME"],
        client_id=client_id,
        client_secret_key=client_secret,
        verify=True,
    )
    return KeycloakAdmin(connection=connection)


@functools.cache
def get_runtime_client() -> KeycloakAdmin:
    config = settings.KEYCLOAK_ADMIN_CONFIG
    return build_keycloak_admin(config["CLIENT_ID"], config["CLIENT_SECRET_KEY"])


@functools.cache
def get_provisioner_client() -> KeycloakAdmin:
    config = settings.KEYCLOAK_PROVISIONER_CONFIG
    return build_keycloak_admin(config["CLIENT_ID"], config["CLIENT_SECRET_KEY"])


def can_authenticate(client_id: str, client_secret: str) -> tuple[bool, str | None]:
    try:
        admin = build_keycloak_admin(client_id, client_secret)
        admin.get_realm(settings.KEYCLOAK_ADMIN_CONFIG["REALM_NAME"])
        return True, None
    except KeycloakAuthenticationError:
        return False, "authentication failed"
    except KeycloakConnectionError:
        return False, "keycloak is not reachable"
    except KeycloakGetError as error:
        if error.response_code == 404:
            return False, "realm does not exist"
        if error.response_code == 403:
            return False, "forbidden"
        return False, f"keycloak returned {error.response_code}"
    except KeycloakError as error:
        return False, str(error)
