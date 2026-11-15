from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from django.conf import settings

from tapir.wirgarten.constants import Permission

REALM_ROLES = tuple(sorted(Permission.all()))
SUPERUSER_GROUP_NAME = "superuser"
REALM_MANAGEMENT_CLIENT_ID = "realm-management"
BACKEND_CLIENT_ROLES = ("manage-users",)
PROVISIONER_CLIENT_ROLES = ("realm-admin",)
PROVISIONER_SECRET_PLACEHOLDER = "**********"

assert REALM_ROLES, "Permission.all() returned no realm roles"
assert len(REALM_ROLES) == len(
    set(REALM_ROLES)
), "Permission.all() contains duplicate roles"
assert "coop.manage" in REALM_ROLES, "coop.manage is part of the Tapir role inventory"


@dataclass(frozen=True)
class RoleSpec:
    name: str
    description: str = ""
    client_role: bool = False
    composite: bool = False

    def to_payload(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "clientRole": self.client_role,
            "composite": self.composite,
        }


@dataclass(frozen=True)
class GroupSpec:
    name: str
    realm_roles: tuple[str, ...]


@dataclass(frozen=True)
class ClientRoleScopeMapping:
    client_id: str
    role_owner_client_id: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class ClientSpec:
    client_id: str
    description: str
    public_client: bool
    service_accounts_enabled: bool
    standard_flow_enabled: bool
    direct_access_grants_enabled: bool
    redirect_uris: tuple[str, ...]
    web_origins: tuple[str, ...]
    secret: str | None = None
    full_scope_allowed: bool = True

    def to_create_payload(self) -> dict:
        payload = {
            "clientId": self.client_id,
            "name": self.client_id,
            "description": self.description,
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": self.public_client,
            "bearerOnly": False,
            "standardFlowEnabled": self.standard_flow_enabled,
            "implicitFlowEnabled": False,
            "directAccessGrantsEnabled": self.direct_access_grants_enabled,
            "serviceAccountsEnabled": self.service_accounts_enabled,
            "redirectUris": list(self.redirect_uris),
            "webOrigins": list(self.web_origins),
            "fullScopeAllowed": self.full_scope_allowed,
        }
        if not self.public_client:
            payload["clientAuthenticatorType"] = "client-secret"
        if self.secret:
            payload["secret"] = self.secret
        return payload

    def to_update_payload(self) -> dict:
        payload = {
            "enabled": True,
            "publicClient": self.public_client,
            "standardFlowEnabled": self.standard_flow_enabled,
            "implicitFlowEnabled": False,
            "directAccessGrantsEnabled": self.direct_access_grants_enabled,
            "serviceAccountsEnabled": self.service_accounts_enabled,
            "redirectUris": list(self.redirect_uris),
            "webOrigins": list(self.web_origins),
            "fullScopeAllowed": self.full_scope_allowed,
        }
        if not self.public_client:
            payload["clientAuthenticatorType"] = "client-secret"
        return payload


@dataclass(frozen=True)
class DesiredState:
    realm_name: str
    realm_settings: dict
    realm_roles: tuple[RoleSpec, ...]
    superuser_group: GroupSpec
    clients: tuple[ClientSpec, ...]
    service_account_roles: dict[str, dict[str, tuple[str, ...]]]
    client_role_scope_mappings: tuple[ClientRoleScopeMapping, ...]
    warnings: tuple[str, ...]


def normalize_site_url(site_url: str) -> str:
    return site_url.rstrip("/")


def build_redirect_uris(
    site_url: str,
    debug: bool,
) -> tuple[str, ...]:
    base = normalize_site_url(site_url)
    uris = [f"{base}/*"]
    if debug:
        uris.extend(
            [
                "http://localhost:8000/*",
                "http://127.0.0.1:8000/*",
                "http://localhost:5173/*",
                "http://127.0.0.1:5173/*",
            ]
        )
    return tuple(dict.fromkeys(uris))


def build_web_origins(
    site_url: str,
    debug: bool,
) -> tuple[str, ...]:
    parsed = urlparse(normalize_site_url(site_url))
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"SITE_URL must be an absolute URL, got {site_url!r}")

    origins = [f"{parsed.scheme}://{parsed.netloc}"]
    if debug:
        origins.extend(
            [
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]
        )
    return tuple(dict.fromkeys(origins))


def build_desired_state() -> DesiredState:
    admin_config = settings.KEYCLOAK_ADMIN_CONFIG
    provisioner_config = settings.KEYCLOAK_PROVISIONER_CONFIG

    redirect_uris = build_redirect_uris(
        settings.SITE_URL,
        settings.DEBUG,
    )
    web_origins = build_web_origins(
        settings.SITE_URL,
        settings.DEBUG,
    )

    warnings = []
    if (
        not settings.DEBUG
        and provisioner_config["CLIENT_SECRET_KEY"] == PROVISIONER_SECRET_PLACEHOLDER
    ):
        warnings.append(
            "KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY is still the placeholder value"
        )

    return DesiredState(
        realm_name=admin_config["REALM_NAME"],
        realm_settings={
            "enabled": True,
            "registrationAllowed": False,
            "registrationEmailAsUsername": True,
            "loginWithEmailAllowed": True,
            "duplicateEmailsAllowed": False,
            "editUsernameAllowed": False,
            "resetPasswordAllowed": True,
            "verifyEmail": True,
        },
        realm_roles=tuple(RoleSpec(name=name) for name in REALM_ROLES),
        superuser_group=GroupSpec(
            name=SUPERUSER_GROUP_NAME,
            realm_roles=REALM_ROLES,
        ),
        clients=(
            ClientSpec(
                client_id=admin_config["CLIENT_ID"],
                description="Tapir backend client used for login and user management",
                public_client=False,
                service_accounts_enabled=True,
                standard_flow_enabled=True,
                direct_access_grants_enabled=False,
                redirect_uris=redirect_uris,
                web_origins=web_origins,
                secret=admin_config["CLIENT_SECRET_KEY"],
                full_scope_allowed=False,
            ),
            ClientSpec(
                client_id=admin_config["FRONTEND_CLIENT_ID"],
                description="Public client used by the Tapir frontend",
                public_client=True,
                service_accounts_enabled=False,
                standard_flow_enabled=True,
                direct_access_grants_enabled=False,
                redirect_uris=redirect_uris,
                web_origins=web_origins,
                full_scope_allowed=False,
            ),
            ClientSpec(
                client_id=provisioner_config["CLIENT_ID"],
                description="Used by manage.py keycloak sync",
                public_client=False,
                service_accounts_enabled=True,
                standard_flow_enabled=False,
                direct_access_grants_enabled=False,
                redirect_uris=(),
                web_origins=(),
                secret=provisioner_config["CLIENT_SECRET_KEY"],
                full_scope_allowed=False,
            ),
        ),
        service_account_roles={
            admin_config["CLIENT_ID"]: {
                REALM_MANAGEMENT_CLIENT_ID: BACKEND_CLIENT_ROLES
            },
            provisioner_config["CLIENT_ID"]: {
                REALM_MANAGEMENT_CLIENT_ID: PROVISIONER_CLIENT_ROLES
            },
        },
        client_role_scope_mappings=(
            ClientRoleScopeMapping(
                client_id=admin_config["CLIENT_ID"],
                role_owner_client_id=REALM_MANAGEMENT_CLIENT_ID,
                roles=BACKEND_CLIENT_ROLES,
            ),
            ClientRoleScopeMapping(
                client_id=provisioner_config["CLIENT_ID"],
                role_owner_client_id=REALM_MANAGEMENT_CLIENT_ID,
                roles=PROVISIONER_CLIENT_ROLES,
            ),
        ),
        warnings=tuple(warnings),
    )
