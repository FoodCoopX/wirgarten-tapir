from __future__ import annotations

from dataclasses import dataclass, field, replace

from django.conf import settings
from keycloak.exceptions import (
    KeycloakAuthenticationError,
    KeycloakConnectionError,
    KeycloakGetError,
    KeycloakOperationError,
)

from tapir.accounts.services.keycloak_client_factory import (
    REASON_AUTHENTICATION_FAILED,
    REASON_MISSING_ADMIN_API_SCOPE,
    can_authenticate,
)
from tapir.accounts.services.keycloak_desired_state import (
    ADMIN_API_CLIENT_SCOPE,
    ClientSpec,
    DesiredState,
    REALM_MANAGEMENT_CLIENT_ID,
)


def _matches(actual, expected) -> bool:
    """Compare Keycloak values without depending on list order.

    Keycloak stores multi-valued client attributes as sets and may return them
    in a different order than the payload that created or updated them.
    """
    if isinstance(expected, (list, tuple)):
        return set(actual or []) == set(expected)
    return actual == expected


AUTH_ERROR_MESSAGE = (
    "The Keycloak provisioning client could not authenticate against "
    f"{settings.KEYCLOAK_ADMIN_CONFIG['SERVER_URL']} in realm "
    f"{settings.KEYCLOAK_ADMIN_CONFIG['REALM_NAME']!r}. Check "
    "KEYCLOAK_PROVISIONER_CLIENT_ID and "
    "KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY. The built-in "
    f"{ADMIN_API_CLIENT_SCOPE} default client scope is also required on "
    "every client that calls the Admin API. For the local stack, import "
    "docker/keycloak/import/tapir-realm.json; for other servers see "
    "docs/admins/keycloak.md."
)

CONNECTION_ERROR_MESSAGE = (
    "Keycloak is not reachable at KEYCLOAK_ADMIN_SERVER_URL="
    f"{settings.KEYCLOAK_ADMIN_CONFIG['SERVER_URL']}. Check DNS, network "
    "access and TLS trust; see docs/admins/keycloak.md."
)
RIGHTS_ERROR_MESSAGE = (
    "The Keycloak provisioning client lacks realm-management/realm-admin. "
    "Assign that role to its service account and add the client scope mapping; "
    "see docs/admins/keycloak.md."
)
REALM_MISSING_MESSAGE = (
    "The Keycloak realm does not exist. Check KEYCLOAK_REALM_NAME or create "
    "the realm first; for the local stack import "
    "docker/keycloak/import/tapir-realm.json. See docs/admins/keycloak.md."
)
ADMIN_API_SCOPE_MISSING_MESSAGE = (
    "The Keycloak server does not provide the built-in client scope "
    f"{ADMIN_API_CLIENT_SCOPE!r}, which current Keycloak releases require for "
    "the Admin REST API. Upgrade Keycloak and rerun the command; see "
    "docs/admins/keycloak.md."
)


@dataclass(frozen=True)
class Change:
    level: str
    section: str
    message: str
    fixable: bool = True
    fixed: bool = False


@dataclass(frozen=True)
class Check:
    section: str
    description: str
    status: str
    details: str = ""


@dataclass
class ReconcileResult:
    changes: list[Change] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_roles: list[str] = field(default_factory=list)
    assigned_roles: list[str] = field(default_factory=list)
    created_clients: list[str] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    role_count: int = 0
    role_present: int = 0
    group_role_count: int = 0
    group_role_present: int = 0
    realm_setting_count: int = 0
    realm_setting_present: int = 0
    client_count: int = 0
    client_present: int = 0
    default_client_scope_count: int = 0
    default_client_scope_present: int = 0
    role_scope_mapping_count: int = 0
    role_scope_mapping_present: int = 0
    service_account_count: int = 0
    service_account_present: int = 0
    superuser_group_present: bool = False
    runtime_secret_ok: bool = False

    @property
    def errors(self) -> list[Change]:
        return [
            change
            for change in self.changes
            if change.level == "error" and not change.fixed
        ]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


class KeycloakSetupError(Exception):
    pass


class KeycloakReconciler:
    def __init__(self, client, desired: DesiredState):
        self.client = client
        self.desired = desired

    def reconcile(self, dry_run: bool) -> ReconcileResult:
        result = ReconcileResult()
        try:
            realm = self._get_realm()
            self._reconcile_realm(realm, result, dry_run)
            self._reconcile_roles(result, dry_run)
            self._reconcile_superuser_group(result, dry_run)
            clients = self._reconcile_clients(result, dry_run)
            self._reconcile_service_accounts(result, dry_run, clients)
            self._reconcile_runtime_secret(result, dry_run, clients)
            self._collect_warnings(realm, result)
        except KeycloakAuthenticationError as error:
            raise KeycloakSetupError(AUTH_ERROR_MESSAGE) from error
        except KeycloakConnectionError as error:
            raise KeycloakSetupError(CONNECTION_ERROR_MESSAGE) from error
        except KeycloakOperationError as error:
            if error.response_code == 403:
                raise KeycloakSetupError(RIGHTS_ERROR_MESSAGE) from error
            raise

        result.warnings.extend(self.desired.warnings)
        return result

    def _get_realm(self) -> dict:
        try:
            return self.client.get_realm(self.desired.realm_name)
        except KeycloakGetError as error:
            if error.response_code == 404:
                raise KeycloakSetupError(REALM_MISSING_MESSAGE) from error
            if error.response_code == 401:
                raise KeycloakSetupError(AUTH_ERROR_MESSAGE) from error
            if error.response_code == 403:
                raise KeycloakSetupError(RIGHTS_ERROR_MESSAGE) from error
            raise

    def _reconcile_realm(
        self, realm: dict, result: ReconcileResult, dry_run: bool
    ) -> None:
        payload = {}
        first_change = len(result.changes)
        for key, expected in self.desired.realm_settings.items():
            actual = realm.get(key)
            if actual != expected:
                payload[key] = expected
                result.changes.append(
                    Change(
                        level="error",
                        section="realm",
                        message=f"{key} is {actual!r}, expected {expected!r}",
                    )
                )

        result.realm_setting_count = len(self.desired.realm_settings)
        result.realm_setting_present = result.realm_setting_count - len(payload)
        result.checks.append(
            Check(
                section="realm",
                description="realm settings",
                status="error" if payload else "ok",
                details=(
                    f"{result.realm_setting_present}/"
                    f"{result.realm_setting_count} match: "
                    + ", ".join(self.desired.realm_settings)
                ),
            )
        )
        if not payload or dry_run:
            return

        self.client.update_realm(self.desired.realm_name, payload)
        for index in range(first_change, len(result.changes)):
            result.changes[index] = replace(result.changes[index], fixed=True)

    def _reconcile_roles(self, result: ReconcileResult, dry_run: bool) -> None:
        existing = {
            role["name"]: role
            for role in self.client.get_realm_roles(brief_representation=True)
        }
        result.role_count = len(self.desired.realm_roles)
        result.role_present = sum(
            1 for role in self.desired.realm_roles if role.name in existing
        )

        for role in self.desired.realm_roles:
            current = existing.get(role.name)
            if current is None:
                if dry_run:
                    result.changes.append(
                        Change(
                            level="error",
                            section="roles",
                            message=f"role {role.name} is missing",
                        )
                    )
                    continue
                self.client.create_realm_role(
                    payload=role.to_payload(), skip_exists=True
                )
                result.created_roles.append(role.name)
                result.changes.append(
                    Change(
                        level="error",
                        section="roles",
                        message=f"role {role.name} is missing",
                        fixed=True,
                    )
                )
                continue

            if current.get("clientRole") not in (None, False) or current.get(
                "composite"
            ) not in (None, False):
                if dry_run:
                    result.changes.append(
                        Change(
                            level="error",
                            section="roles",
                            message=(
                                f"role {role.name} has clientRole="
                                f"{current.get('clientRole')!r} composite="
                                f"{current.get('composite')!r}"
                            ),
                        )
                    )
                    continue
                self.client.update_realm_role(role.name, payload=role.to_payload())
                result.changes.append(
                    Change(
                        level="error",
                        section="roles",
                        message=(f"role {role.name} had wrong role flags"),
                        fixed=True,
                    )
                )

        result.checks.append(
            Check(
                section="roles",
                description="realm roles",
                status=("ok" if result.role_present == result.role_count else "error"),
                details=(
                    f"{result.role_present}/{result.role_count} present: "
                    + ", ".join(role.name for role in self.desired.realm_roles)
                ),
            )
        )

    def _reconcile_superuser_group(
        self, result: ReconcileResult, dry_run: bool
    ) -> None:
        group = self._get_superuser_group(result, dry_run)
        if group is None:
            result.superuser_group_present = False
            result.checks.append(
                Check(
                    section="group",
                    description="superuser group",
                    status="error",
                    details="missing",
                )
            )
            return

        result.superuser_group_present = True

        current_roles = {
            role["name"]
            for role in self.client.get_group_realm_roles(
                group["id"], brief_representation=True
            )
        }
        desired_names = {role.name for role in self.desired.realm_roles}
        result.group_role_count = len(desired_names)
        result.group_role_present = len(desired_names & current_roles)

        missing = [
            role for role in self.desired.realm_roles if role.name not in current_roles
        ]
        for role in missing:
            result.changes.append(
                Change(
                    level="error",
                    section="group",
                    message=(
                        f"group {self.desired.superuser_group.name} is "
                        f"missing role {role.name}"
                    ),
                    fixed=not dry_run,
                )
            )

        if missing and not dry_run:
            representations = [
                self.client.get_realm_role(role.name) for role in missing
            ]
            self.client.assign_group_realm_roles(group["id"], representations)
            result.assigned_roles.extend(role.name for role in missing)

        extra = current_roles - desired_names
        if extra:
            result.changes.append(
                Change(
                    level="warning",
                    section="group",
                    message=(
                        f"group {self.desired.superuser_group.name} has "
                        f"additional roles: {', '.join(sorted(extra))}"
                    ),
                    fixable=False,
                )
            )

        result.checks.append(
            Check(
                section="group",
                description="superuser group",
                status=(
                    "ok"
                    if result.group_role_present == result.group_role_count
                    else "error"
                ),
                details=(
                    f"present, {result.group_role_present}/"
                    f"{result.group_role_count} roles"
                ),
            )
        )

    def _get_superuser_group(
        self, result: ReconcileResult, dry_run: bool
    ) -> dict | None:
        path = f"/{self.desired.superuser_group.name}"
        try:
            return self.client.get_group_by_path(path)
        except KeycloakGetError as error:
            if error.response_code != 404:
                raise
            result.changes.append(
                Change(
                    level="error",
                    section="group",
                    message=f"group {self.desired.superuser_group.name} is missing",
                    fixed=not dry_run,
                )
            )
            if dry_run:
                return None
            self.client.create_group({"name": self.desired.superuser_group.name})
            return self.client.get_group_by_path(path)

    def _reconcile_clients(
        self, result: ReconcileResult, dry_run: bool
    ) -> dict[str, dict]:
        existing = {
            client["clientId"]: client
            for client in self.client.get_clients()
            if "clientId" in client
        }
        clients: dict[str, dict] = {}
        result.client_count = len(self.desired.clients)
        result.default_client_scope_count = sum(
            len(spec.default_client_scopes) for spec in self.desired.clients
        )
        result.role_scope_mapping_count = sum(
            len(mapping.roles) for mapping in self.desired.client_role_scope_mappings
        )
        client_ok = True
        for spec in self.desired.clients:
            current = existing.get(spec.client_id)
            if current is None:
                result.changes.append(
                    Change(
                        level="error",
                        section="clients",
                        message=f"client {spec.client_id} is missing",
                        fixed=not dry_run,
                    )
                )
                client_ok = False
                if dry_run:
                    continue
                self.client.create_client(spec.to_create_payload(), skip_exists=True)
                result.created_clients.append(spec.client_id)
                current = self._get_client(spec.client_id)
            else:
                current = self._ensure_client_detail(current)

            clients[spec.client_id] = current
            self._reconcile_default_client_scopes(spec, current, result, dry_run)
            self._reconcile_client_role_scope_mappings(spec, result, dry_run)
            payload = spec.to_update_payload()
            drift = {
                key: (current.get(key), expected)
                for key, expected in payload.items()
                if not _matches(current.get(key), expected)
            }
            if not drift:
                continue

            client_ok = False

            for key, (actual, expected) in drift.items():
                result.changes.append(
                    Change(
                        level="error",
                        section="clients",
                        message=(
                            f"client {spec.client_id}: {key} is {actual!r}, "
                            f"expected {expected!r}"
                        ),
                        fixed=not dry_run,
                    )
                )
            if not dry_run:
                self.client.update_client(
                    self.client.get_client_id(spec.client_id), payload
                )
                clients[spec.client_id] = self._get_client(spec.client_id)

        result.client_present = len(clients)
        result.checks.append(
            Check(
                section="clients",
                description="clients",
                status=(
                    "ok"
                    if client_ok and result.client_present == result.client_count
                    else "error"
                ),
                details=(
                    f"{result.client_present}/{result.client_count} present: "
                    + ", ".join(spec.client_id for spec in self.desired.clients)
                    + "; flags, redirect URIs, web origins checked"
                ),
            )
        )
        result.checks.append(
            Check(
                section="clients",
                description="default client scopes",
                status=(
                    "ok"
                    if result.default_client_scope_present
                    == result.default_client_scope_count
                    else "error"
                ),
                details=(
                    f"{result.default_client_scope_present}/"
                    f"{result.default_client_scope_count} "
                    "(kc-admin-api on the clients that call the Admin API)"
                ),
            )
        )
        mapping_details = ", ".join(
            f"{mapping.client_id} -> " f"{mapping.role_owner_client_id}/{role}"
            for mapping in self.desired.client_role_scope_mappings
            for role in mapping.roles
        )
        result.checks.append(
            Check(
                section="clients",
                description="client role scope mappings",
                status=(
                    "ok"
                    if result.role_scope_mapping_present
                    == result.role_scope_mapping_count
                    else "error"
                ),
                details=(
                    f"{result.role_scope_mapping_present}/"
                    f"{result.role_scope_mapping_count}: {mapping_details}"
                ),
            )
        )

        return clients

    def _ensure_client_detail(self, client: dict) -> dict:
        if "redirectUris" in client and "webOrigins" in client:
            return client
        internal_id = client.get("id") or self.client.get_client_id(client["clientId"])
        return self.client.get_client(internal_id)

    def _get_client(self, client_id: str) -> dict:
        internal_id = self.client.get_client_id(client_id)
        if internal_id is None:
            return {}
        return self.client.get_client(internal_id)

    def _reconcile_default_client_scopes(
        self,
        spec: ClientSpec,
        client: dict,
        result: ReconcileResult,
        dry_run: bool,
    ) -> None:
        if not spec.default_client_scopes:
            return

        internal_id = client.get("id") or self.client.get_client_id(spec.client_id)
        current = {
            scope["name"]
            for scope in self.client.get_client_default_client_scopes(internal_id)
        }
        present = set(current)
        missing = [name for name in spec.default_client_scopes if name not in current]
        if not missing:
            result.default_client_scope_present += len(
                present & set(spec.default_client_scopes)
            )
            return

        available = {scope["name"]: scope for scope in self.client.get_client_scopes()}
        for name in missing:
            scope = available.get(name)
            if scope is None:
                result.changes.append(
                    Change(
                        level="error",
                        section="clients",
                        message=ADMIN_API_SCOPE_MISSING_MESSAGE,
                        fixable=False,
                    )
                )
                continue

            result.changes.append(
                Change(
                    level="error",
                    section="clients",
                    message=(
                        f"client {spec.client_id} is missing default client scope "
                        f"{name}"
                    ),
                    fixed=not dry_run,
                )
            )
            if dry_run:
                continue
            self.client.add_client_default_client_scope(
                internal_id,
                scope["id"],
                {
                    "realm": self.desired.realm_name,
                    "client": internal_id,
                    "clientScopeId": scope["id"],
                },
            )
            present.add(name)

        result.default_client_scope_present += len(
            present & set(spec.default_client_scopes)
        )

    def _reconcile_client_role_scope_mappings(
        self, spec: ClientSpec, result: ReconcileResult, dry_run: bool
    ) -> None:
        for mapping in self.desired.client_role_scope_mappings:
            if mapping.client_id != spec.client_id:
                continue

            client_uuid = self.client.get_client_id(spec.client_id)
            owner_uuid = self.client.get_client_id(mapping.role_owner_client_id)
            if client_uuid is None or owner_uuid is None:
                continue

            current = {
                role["name"]
                for role in self.client.get_client_roles_of_client_scope(
                    client_uuid, owner_uuid
                )
            }
            present = set(current)
            missing = [name for name in mapping.roles if name not in current]
            for name in missing:
                result.changes.append(
                    Change(
                        level="error",
                        section="clients",
                        message=(
                            f"client {spec.client_id} is missing role scope "
                            f"mapping {mapping.role_owner_client_id}/{name}"
                        ),
                        fixed=not dry_run,
                    )
                )

            if missing and not dry_run:
                representations = [
                    self.client.get_client_role(owner_uuid, name) for name in missing
                ]
                self.client.assign_client_roles_to_client_scope(
                    client_uuid, owner_uuid, representations
                )
                present.update(missing)

            extra = current - set(mapping.roles)
            if extra:
                result.changes.append(
                    Change(
                        level="warning",
                        section="clients",
                        message=(
                            f"client {spec.client_id} has additional role scope "
                            f"mappings: {', '.join(sorted(extra))}"
                        ),
                        fixable=False,
                    )
                )

            result.role_scope_mapping_present += len(present & set(mapping.roles))

    def _reconcile_service_accounts(
        self,
        result: ReconcileResult,
        dry_run: bool,
        clients: dict[str, dict],
    ) -> None:
        result.service_account_count = sum(
            len(role_names)
            for mappings in self.desired.service_account_roles.values()
            for role_names in mappings.values()
        )
        for client_id, mappings in self.desired.service_account_roles.items():
            client = clients.get(client_id)
            if client is None:
                result.changes.append(
                    Change(
                        level="error",
                        section="service-accounts",
                        message=(
                            f"cannot check the service account of missing "
                            f"client {client_id}"
                        ),
                        fixable=False,
                    )
                )
                continue

            internal_id = client.get("id") or self.client.get_client_id(client_id)
            try:
                user = self.client.get_client_service_account_user(internal_id)
            except KeycloakGetError as error:
                if error.response_code != 404:
                    raise
                result.changes.append(
                    Change(
                        level="error",
                        section="service-accounts",
                        message=f"client {client_id} has no service account",
                        fixable=False,
                    )
                )
                continue

            for management_client_id, role_names in mappings.items():
                management_client_uuid = self.client.get_client_id(management_client_id)
                current = {
                    role["name"]
                    for role in self.client.get_client_roles_of_user(
                        user["id"], management_client_uuid
                    )
                }
                result.service_account_present += len(set(role_names) & current)
                missing = [name for name in role_names if name not in current]
                for name in missing:
                    result.changes.append(
                        Change(
                            level="error",
                            section="service-accounts",
                            message=(
                                f"service account of {client_id} is missing "
                                f"{management_client_id}/{name}"
                            ),
                            fixed=not dry_run,
                        )
                    )
                if missing and not dry_run:
                    representations = [
                        self.client.get_client_role(management_client_uuid, name)
                        for name in missing
                    ]
                    self.client.assign_client_role(
                        user["id"], management_client_uuid, representations
                    )

        service_account_details = ", ".join(
            f"{client_id} -> {management_client_id}/{role}"
            for client_id, mappings in self.desired.service_account_roles.items()
            for management_client_id, role_names in mappings.items()
            for role in role_names
        )
        result.checks.append(
            Check(
                section="service-accounts",
                description="service account roles",
                status=(
                    "ok"
                    if result.service_account_present == result.service_account_count
                    else "error"
                ),
                details=(
                    f"{result.service_account_present}/"
                    f"{result.service_account_count}: {service_account_details}"
                ),
            )
        )

    def _reconcile_runtime_secret(
        self,
        result: ReconcileResult,
        dry_run: bool,
        clients: dict[str, dict],
    ) -> None:
        admin_config = settings.KEYCLOAK_ADMIN_CONFIG
        backend = clients.get(admin_config["CLIENT_ID"])
        if backend is None:
            result.runtime_secret_ok = False
            result.checks.append(
                Check(
                    section="runtime-secret",
                    description="runtime client secret",
                    status="error",
                    details=f"skipped: {admin_config['CLIENT_ID']} is missing",
                )
            )
            return

        can_login, reason = can_authenticate(
            admin_config["CLIENT_ID"], admin_config["CLIENT_SECRET_KEY"]
        )
        if can_login:
            result.runtime_secret_ok = True
            result.checks.append(
                Check(
                    section="runtime-secret",
                    description="runtime client secret",
                    status="ok",
                    details=f"{admin_config['CLIENT_ID']} can authenticate",
                )
            )
            return

        if reason == REASON_MISSING_ADMIN_API_SCOPE:
            result.runtime_secret_ok = False
            result.changes.append(
                Change(
                    level="error",
                    section="clients",
                    message=(
                        f"client {admin_config['CLIENT_ID']} cannot call the "
                        f"Admin API: {reason}"
                    ),
                    fixable=False,
                )
            )
            result.checks.append(
                Check(
                    section="runtime-secret",
                    description="runtime client secret",
                    status="error",
                    details=(
                        f"{admin_config['CLIENT_ID']} cannot call the Admin API: "
                        f"{reason}"
                    ),
                )
            )
            return

        result.runtime_secret_ok = False
        result.changes.append(
            Change(
                level="error",
                section="clients",
                message=(
                    f"client {admin_config['CLIENT_ID']} cannot authenticate "
                    f"with the configured secret ({reason})"
                ),
                fixed=not dry_run,
            )
        )
        if dry_run or reason != REASON_AUTHENTICATION_FAILED:
            result.checks.append(
                Check(
                    section="runtime-secret",
                    description="runtime client secret",
                    status="error",
                    details=(
                        f"{admin_config['CLIENT_ID']} cannot authenticate with "
                        f"the configured secret ({reason})"
                    ),
                )
            )
            return

        internal_id = backend.get("id") or self.client.get_client_id(
            admin_config["CLIENT_ID"]
        )
        self.client.update_client(
            internal_id, {"secret": admin_config["CLIENT_SECRET_KEY"]}
        )
        can_login, reason = can_authenticate(
            admin_config["CLIENT_ID"], admin_config["CLIENT_SECRET_KEY"]
        )
        if not can_login:
            result.runtime_secret_ok = False
            result.changes.append(
                Change(
                    level="error",
                    section="clients",
                    message=(
                        f"client {admin_config['CLIENT_ID']} still cannot "
                        f"authenticate after setting the secret ({reason})"
                    ),
                    fixable=False,
                )
            )
            result.checks.append(
                Check(
                    section="runtime-secret",
                    description="runtime client secret",
                    status="error",
                    details=(
                        f"{admin_config['CLIENT_ID']} still cannot authenticate "
                        f"after setting the secret ({reason})"
                    ),
                )
            )
            return

        result.runtime_secret_ok = True
        result.checks.append(
            Check(
                section="runtime-secret",
                description="runtime client secret",
                status="ok",
                details=(
                    f"{admin_config['CLIENT_ID']} can authenticate after setting "
                    "the secret"
                ),
            )
        )

    def _collect_warnings(self, realm: dict, result: ReconcileResult) -> None:
        smtp = realm.get("smtpServer") or {}
        smtp_configured = bool(smtp.get("host") and smtp.get("from"))
        result.checks.append(
            Check(
                section="smtp",
                description="SMTP server",
                status="ok" if smtp_configured else "warning",
                details=(
                    "host and sender configured"
                    if smtp_configured
                    else "not configured"
                ),
            )
        )
        if not smtp_configured:
            result.changes.append(
                Change(
                    level="warning",
                    section="realm",
                    message="smtpServer is not configured",
                    fixable=False,
                )
            )
