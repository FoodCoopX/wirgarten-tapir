from __future__ import annotations

import base64
import functools
import json

from django.conf import settings
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from keycloak.exceptions import (
    KeycloakAuthenticationError,
    KeycloakConnectionError,
    KeycloakError,
    KeycloakGetError,
)

from tapir.accounts.services.keycloak_desired_state import ADMIN_API_CLIENT_SCOPE

REASON_AUTHENTICATION_FAILED = "authentication failed"
REASON_MISSING_ADMIN_API_SCOPE = (
    "the Admin API rejected the token because it lacks the kc-admin-api scope"
)


def build_keycloak_admin(client_id: str, client_secret: str) -> KeycloakAdmin:
    config = settings.KEYCLOAK_ADMIN_CONFIG
    connection = KeycloakOpenIDConnection(
        # python-keycloak joins relative API paths onto this base URL. The
        # trailing slash makes urljoin keep an optional path prefix such as /auth.
        server_url=config["SERVER_URL"].rstrip("/") + "/",
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


def _token_scope(admin: KeycloakAdmin) -> set[str]:
    """Read the scope claim from the access token python-keycloak obtained.

    The token was just issued by the server, so it is decoded locally instead of
    adding a signature check that can_authenticate is not meant to perform.
    """
    token = admin.connection.token or {}
    access_token = token.get("access_token")
    if not access_token or access_token.count(".") != 2:
        return set()
    payload = access_token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except ValueError:
        return set()
    return set(claims.get("scope", "").split())


def can_authenticate(client_id: str, client_secret: str) -> tuple[bool, str | None]:
    admin = None
    try:
        admin = build_keycloak_admin(client_id, client_secret)
        admin.get_realm(settings.KEYCLOAK_ADMIN_CONFIG["REALM_NAME"])
        return True, None
    except KeycloakAuthenticationError:
        scopes = _token_scope(admin) if admin is not None else set()
        if scopes and ADMIN_API_CLIENT_SCOPE not in scopes:
            return False, REASON_MISSING_ADMIN_API_SCOPE
        return False, REASON_AUTHENTICATION_FAILED
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
