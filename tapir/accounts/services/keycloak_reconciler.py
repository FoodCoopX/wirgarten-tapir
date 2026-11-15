from __future__ import annotations

from dataclasses import dataclass, field, replace

from django.conf import settings
from keycloak.exceptions import (
    KeycloakAuthenticationError,
    KeycloakConnectionError,
    KeycloakGetError,
    KeycloakOperationError,
)

from tapir.accounts.services.keycloak_client_factory import can_authenticate
from tapir.accounts.services.keycloak_desired_state import (
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
    "The Keycloak provisioning client could not authenticate. "
    "Import docker/keycloak/import/tapir-realm.json or set "
    "KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY."
)
CONNECTION_ERROR_MESSAGE = (
    "Keycloak is not reachable at " f"{settings.KEYCLOAK_ADMIN_CONFIG['SERVER_URL']}."
)
RIGHTS_ERROR_MESSAGE = (
    "The Keycloak provisioning client lacks realm-management/realm-admin."
)
REALM_MISSING_MESSAGE = (
    "The Keycloak realm does not exist. Import "
    "docker/keycloak/import/tapir-realm.json first."
)


@dataclass(frozen=True)
class Change:
    level: str
    section: str
    message: str
    fixable: bool = True
    fixed: bool = False


@dataclass
class ReconcileResult:
    changes: list[Change] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_roles: list[str] = field(default_factory=list)
    assigned_roles: list[str] = field(default_factory=list)
    created_clients: list[str] = field(default_factory=list)
    role_count: int = 0
    role_present: int = 0
    group_role_count: int = 0
    group_role_present: int = 0

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

    def _reconcile_superuser_group(
        self, result: ReconcileResult, dry_run: bool
    ) -> None:
        group = self._get_superuser_group(result, dry_run)
        if group is None:
            return

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
                if dry_run:
                    continue
                self.client.create_client(spec.to_create_payload(), skip_exists=True)
                result.created_clients.append(spec.client_id)
                current = self._get_client(spec.client_id)
            else:
                current = self._ensure_client_detail(current)

            clients[spec.client_id] = current
            self._reconcile_client_role_scope_mappings(spec, result, dry_run)
            payload = spec.to_update_payload()
            drift = {
                key: (current.get(key), expected)
                for key, expected in payload.items()
                if not _matches(current.get(key), expected)
            }
            if not drift:
                continue

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

    def _reconcile_service_accounts(
        self,
        result: ReconcileResult,
        dry_run: bool,
        clients: dict[str, dict],
    ) -> None:
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

    def _reconcile_runtime_secret(
        self,
        result: ReconcileResult,
        dry_run: bool,
        clients: dict[str, dict],
    ) -> None:
        admin_config = settings.KEYCLOAK_ADMIN_CONFIG
        backend = clients.get(admin_config["CLIENT_ID"])
        if backend is None:
            return

        can_login, reason = can_authenticate(
            admin_config["CLIENT_ID"], admin_config["CLIENT_SECRET_KEY"]
        )
        if can_login:
            return

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
        if dry_run:
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

    def _collect_warnings(self, realm: dict, result: ReconcileResult) -> None:
        smtp = realm.get("smtpServer") or {}
        if not smtp.get("host") or not smtp.get("from"):
            result.changes.append(
                Change(
                    level="warning",
                    section="realm",
                    message="smtpServer is not configured",
                    fixable=False,
                )
            )
