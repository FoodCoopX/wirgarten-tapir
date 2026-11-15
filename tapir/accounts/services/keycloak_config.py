from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from django.conf import settings

DEFAULT_SERVER_URL = "http://keycloak:8080"
DEFAULT_PUBLIC_URL = "http://localhost:8080"


@dataclass(frozen=True)
class KeycloakConfigIssue:
    level: str
    variable: str
    message: str

    def format(self) -> str:
        return f"{self.variable}: {self.message}"


@dataclass(frozen=True)
class KeycloakConfigCheck:
    errors: tuple[KeycloakConfigIssue, ...]
    warnings: tuple[KeycloakConfigIssue, ...]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


def _is_absolute_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _looks_like_realm_url(value: str) -> bool:
    path = urlparse(value).path.rstrip("/")
    return "/realms/" in path or path.endswith("/realms")


def _origin(value: str) -> tuple[str, str]:
    parsed = urlparse(value)
    return parsed.scheme, parsed.netloc


def build_keycloak_config_summary() -> dict:
    admin_config = settings.KEYCLOAK_ADMIN_CONFIG
    provisioner_config = settings.KEYCLOAK_PROVISIONER_CONFIG
    return {
        "server_url": admin_config["SERVER_URL"].rstrip("/"),
        "public_url": admin_config["PUBLIC_URL"].rstrip("/"),
        "realm": admin_config["REALM_NAME"],
        "client_id": admin_config["CLIENT_ID"],
        "frontend_client_id": admin_config["FRONTEND_CLIENT_ID"],
        "provisioner_client_id": provisioner_config["CLIENT_ID"],
        "site_url": settings.SITE_URL.rstrip("/"),
        "debug": bool(settings.DEBUG),
    }


def check_keycloak_config() -> KeycloakConfigCheck:
    admin_config = settings.KEYCLOAK_ADMIN_CONFIG
    provisioner_config = settings.KEYCLOAK_PROVISIONER_CONFIG
    server_url = admin_config["SERVER_URL"]
    public_url = admin_config["PUBLIC_URL"]
    realm_name = admin_config["REALM_NAME"]
    site_url = settings.SITE_URL

    errors: list[KeycloakConfigIssue] = []
    warnings: list[KeycloakConfigIssue] = []

    def error(variable: str, message: str) -> None:
        errors.append(KeycloakConfigIssue("error", variable, message))

    def warning(variable: str, message: str) -> None:
        warnings.append(KeycloakConfigIssue("warning", variable, message))

    if not server_url:
        error("KEYCLOAK_ADMIN_SERVER_URL", "must not be empty")
    elif not _is_absolute_http_url(server_url):
        error(
            "KEYCLOAK_ADMIN_SERVER_URL",
            f"must be an absolute http(s) URL, got {server_url!r}",
        )
    elif _looks_like_realm_url(server_url):
        error(
            "KEYCLOAK_ADMIN_SERVER_URL",
            "must be the Keycloak base URL without /realms/<realm>",
        )

    if not public_url:
        error("KEYCLOAK_PUBLIC_URL", "must not be empty")
    elif not _is_absolute_http_url(public_url):
        error(
            "KEYCLOAK_PUBLIC_URL",
            f"must be an absolute http(s) URL, got {public_url!r}",
        )
    elif _looks_like_realm_url(public_url):
        error(
            "KEYCLOAK_PUBLIC_URL",
            "must be the Keycloak base URL without /realms/<realm>",
        )

    if not realm_name:
        error("KEYCLOAK_REALM_NAME", "must not be empty")
    elif "/" in realm_name:
        error(
            "KEYCLOAK_REALM_NAME",
            f"must be a realm name without '/', got {realm_name!r}",
        )

    client_ids = {
        "KEYCLOAK_CLIENT_ID": admin_config["CLIENT_ID"],
        "KEYCLOAK_FRONTEND_CLIENT_ID": admin_config["FRONTEND_CLIENT_ID"],
        "KEYCLOAK_PROVISIONER_CLIENT_ID": provisioner_config["CLIENT_ID"],
    }
    for variable, client_id in client_ids.items():
        if not client_id:
            error(variable, "must not be empty")

    configured_client_ids = [
        client_id for client_id in client_ids.values() if client_id
    ]
    if len(configured_client_ids) != len(set(configured_client_ids)):
        error(
            "KEYCLOAK_CLIENT_ID",
            "the backend, frontend and provisioner client IDs must be distinct",
        )

    if not admin_config["CLIENT_SECRET_KEY"]:
        error("KEYCLOAK_ADMIN_CLIENT_SECRET_KEY", "must not be empty")
    if not provisioner_config["CLIENT_SECRET_KEY"]:
        error("KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY", "must not be empty")

    if not site_url:
        error("SITE_URL", "must not be empty")
    elif not _is_absolute_http_url(site_url):
        error("SITE_URL", f"must be an absolute http(s) URL, got {site_url!r}")

    if not settings.DEBUG:
        if server_url.rstrip("/") == DEFAULT_SERVER_URL:
            warning(
                "KEYCLOAK_ADMIN_SERVER_URL",
                "is still the Docker-internal default; set it to the Keycloak "
                "URL of this deployment",
            )
        if public_url.rstrip("/") == DEFAULT_PUBLIC_URL:
            warning(
                "KEYCLOAK_PUBLIC_URL",
                "is still the local default; browsers will be redirected to localhost",
            )
        if urlparse(site_url).hostname in {"localhost", "127.0.0.1"}:
            warning(
                "SITE_URL",
                "points to a local host; the Keycloak redirect URIs will only be "
                "valid locally",
            )
        if (
            _is_absolute_http_url(server_url)
            and _is_absolute_http_url(public_url)
            and _origin(server_url) != _origin(public_url)
        ):
            warning(
                "KEYCLOAK_PUBLIC_URL",
                "has a different origin than KEYCLOAK_ADMIN_SERVER_URL; the OIDC "
                "login uses the admin URL while the password redirect and CSP use "
                "the public URL",
            )

    return KeycloakConfigCheck(errors=tuple(errors), warnings=tuple(warnings))
