from __future__ import annotations

from copy import deepcopy

from keycloak.exceptions import KeycloakConnectionError, KeycloakGetError

STANDARD_USER_PROFILE = {
    "attributes": [
        {"name": "username", "displayName": "${username}"},
        {"name": "email", "displayName": "${email}"},
        {"name": "firstName", "displayName": "${firstName}"},
        {"name": "lastName", "displayName": "${lastName}"},
    ],
    "groups": [],
}


DEFAULT_REALM = {
    "enabled": True,
    "registrationAllowed": False,
    "registrationEmailAsUsername": True,
    "loginWithEmailAllowed": True,
    "duplicateEmailsAllowed": False,
    "editUsernameAllowed": False,
    "resetPasswordAllowed": True,
    "verifyEmail": True,
    "smtpServer": {
        "host": "list.example.com",
        "from": "keycloak@example.com",
    },
}

BUILTIN_ROLE_NAMES = (
    "default-roles-tapir",
    "offline_access",
    "uma_authorization",
)

REALM_DEFAULT_CLIENT_SCOPES = (
    "web-origins",
    "acr",
    "roles",
    "profile",
    "basic",
    "email",
)


class FakeKeycloakAdmin:
    def __init__(
        self,
        realm: dict | None = None,
        roles: dict[str, dict] | None = None,
        groups: list[dict] | None = None,
        clients: list[dict] | None = None,
        service_account_roles: dict[str, dict[str, set[str]]] | None = None,
        client_scope_roles: dict[tuple[str, str], set[str]] | None = None,
        profile: dict | None = None,
        realm_error_code: int | None = None,
        profile_error_code: int | None = None,
        connection_error: bool = False,
    ):
        self.realm = deepcopy(DEFAULT_REALM if realm is None else realm)
        self.roles = roles if roles is not None else {}
        self.groups = groups if groups is not None else []
        self.clients = clients if clients is not None else []
        self.service_account_roles = (
            service_account_roles if service_account_roles is not None else {}
        )
        self.client_scope_roles = (
            client_scope_roles if client_scope_roles is not None else {}
        )
        self.profile = deepcopy(STANDARD_USER_PROFILE if profile is None else profile)
        self.profile_error_code = profile_error_code
        self.realm_error_code = realm_error_code
        self.connection_error = connection_error
        self.client_scope_names = [
            *REALM_DEFAULT_CLIENT_SCOPES,
            "offline_access",
            "kc-admin-api",
        ]
        self.calls: list[tuple] = []

    @classmethod
    def converged(cls, desired) -> "FakeKeycloakAdmin":
        roles = {
            name: {
                "id": f"role-{name}",
                "name": name,
                "description": "",
                "clientRole": False,
                "composite": False,
            }
            for name in desired.superuser_group.realm_roles
        }
        for name in BUILTIN_ROLE_NAMES:
            roles[name] = {
                "id": f"role-{name}",
                "name": name,
                "description": "",
                "clientRole": False,
                "composite": False,
            }

        groups = [
            {
                "id": "group-superuser",
                "name": desired.superuser_group.name,
                "path": f"/{desired.superuser_group.name}",
                "realmRoles": list(desired.superuser_group.realm_roles),
                "subGroups": [],
            }
        ]

        clients = [{"id": "client-realm-management", "clientId": "realm-management"}]
        service_account_roles = {}
        for spec in desired.clients:
            payload = spec.to_create_payload()
            payload["id"] = f"client-{spec.client_id}"
            payload["defaultClientScopes"] = list(
                dict.fromkeys(
                    (*REALM_DEFAULT_CLIENT_SCOPES, *spec.default_client_scopes)
                )
            )
            clients.append(payload)
            roles_for_client = desired.service_account_roles.get(spec.client_id, {})
            service_account_roles[spec.client_id] = {
                "realm-management": set(roles_for_client.get("realm-management", set()))
            }

        client_scope_roles = {}
        for mapping in desired.client_role_scope_mappings:
            client_scope_roles[
                (
                    f"client-{mapping.client_id}",
                    f"client-{mapping.role_owner_client_id}",
                )
            ] = set(mapping.roles)
        return cls(
            roles=roles,
            groups=groups,
            clients=clients,
            service_account_roles=service_account_roles,
            client_scope_roles=client_scope_roles,
            profile=(
                deepcopy(desired.user_profile)
                if desired.user_profile is not None
                else deepcopy(STANDARD_USER_PROFILE)
            ),
        )

    def get_realm(self, realm_name: str) -> dict:
        self.calls.append(("get_realm", realm_name))
        if self.connection_error:
            raise KeycloakConnectionError("connection refused")
        if self.realm_error_code is not None:
            raise KeycloakGetError("realm error", response_code=self.realm_error_code)
        return deepcopy(self.realm)

    def update_realm(self, realm_name: str, payload: dict) -> dict:
        self.calls.append(("update_realm", realm_name, payload))
        self.realm.update(payload)
        return {}

    def get_realm_users_profile(self) -> dict:
        self.calls.append(("get_realm_users_profile",))
        if self.profile_error_code is not None:
            raise KeycloakGetError(
                "user profile error", response_code=self.profile_error_code
            )
        return deepcopy(self.profile)

    def update_realm_users_profile(self, payload: dict) -> dict:
        self.calls.append(("update_realm_users_profile", payload))
        self.profile = deepcopy(payload)
        return {}

    def get_realm_roles(self, brief_representation: bool = True) -> list:
        self.calls.append(("get_realm_roles", brief_representation))
        return [deepcopy(role) for role in self.roles.values()]

    def create_realm_role(self, payload: dict, skip_exists: bool = False) -> str:
        self.calls.append(("create_realm_role", payload, skip_exists))
        name = payload["name"]
        if name in self.roles:
            return name
        self.roles[name] = {
            **payload,
            "id": f"role-{name}",
        }
        return name

    def update_realm_role(self, role_name: str, payload: dict) -> dict:
        self.calls.append(("update_realm_role", role_name, payload))
        self.roles[role_name].update(payload)
        return {}

    def get_realm_role(self, role_name: str) -> dict:
        self.calls.append(("get_realm_role", role_name))
        if role_name not in self.roles:
            raise KeycloakGetError("role not found", response_code=404)
        return deepcopy(self.roles[role_name])

    def get_group_by_path(self, path: str) -> dict:
        self.calls.append(("get_group_by_path", path))
        name = path.rsplit("/", 1)[-1]
        for group in self.groups:
            if group["name"] == name:
                return deepcopy(group)
        raise KeycloakGetError("group not found", response_code=404)

    def create_group(
        self, payload: dict, parent: str | None = None, skip_exists: bool = False
    ) -> str:
        self.calls.append(("create_group", payload))
        group = {
            "id": f"group-{payload['name']}",
            "name": payload["name"],
            "path": f"/{payload['name']}",
            "realmRoles": [],
            "subGroups": [],
        }
        self.groups.append(group)
        return group["id"]

    def get_group_realm_roles(
        self, group_id: str, brief_representation: bool = True
    ) -> list:
        self.calls.append(("get_group_realm_roles", group_id))
        group = self._group_by_id(group_id)
        return [
            deepcopy(self.roles[name])
            for name in group["realmRoles"]
            if name in self.roles
        ]

    def assign_group_realm_roles(self, group_id: str, roles) -> dict:
        self.calls.append(("assign_group_realm_roles", group_id, roles))
        group = self._group_by_id(group_id)
        for role in roles:
            if role["name"] not in group["realmRoles"]:
                group["realmRoles"].append(role["name"])
        return {}

    def get_clients(self) -> list:
        self.calls.append(("get_clients",))
        return [deepcopy(client) for client in self.clients]

    def get_client_id(self, client_id: str) -> str | None:
        for client in self.clients:
            if client["clientId"] == client_id:
                return client["id"]
        return None

    def get_client(self, client_id: str) -> dict:
        for client in self.clients:
            if client["id"] == client_id:
                return deepcopy(client)
        raise KeycloakGetError("client not found", response_code=404)

    def create_client(self, payload: dict, skip_exists: bool = False) -> str:
        self.calls.append(("create_client", payload, skip_exists))
        existing = self.get_client_id(payload["clientId"])
        if existing is not None:
            return existing
        client = {**payload, "id": f"client-{payload['clientId']}"}
        self.clients.append(client)
        self.service_account_roles.setdefault(payload["clientId"], {})
        return client["id"]

    def update_client(self, client_id: str, payload: dict) -> dict:
        self.calls.append(("update_client", client_id, payload))
        for client in self.clients:
            if client["id"] == client_id:
                client.update(payload)
                return {}
        raise KeycloakGetError("client not found", response_code=404)

    def get_client_service_account_user(self, client_id: str) -> dict:
        self.calls.append(("get_client_service_account_user", client_id))
        client = self.get_client(client_id)
        return {
            "id": f"service-account-{client['clientId']}",
            "username": f"service-account-{client['clientId']}",
        }

    def get_client_default_client_scopes(self, client_id: str) -> list:
        self.calls.append(("get_client_default_client_scopes", client_id))
        client = self.get_client(client_id)
        return [
            {"id": f"scope-{name}", "name": name}
            for name in client.get("defaultClientScopes", [])
        ]

    def get_client_scopes(self) -> list:
        self.calls.append(("get_client_scopes",))
        return [
            {"id": f"scope-{name}", "name": name} for name in self.client_scope_names
        ]

    def add_client_default_client_scope(
        self, client_id: str, client_scope_id: str, payload: dict
    ) -> dict:
        self.calls.append(
            ("add_client_default_client_scope", client_id, client_scope_id, payload)
        )
        name = client_scope_id.removeprefix("scope-")
        client = self.get_client(client_id)
        scopes = client.setdefault("defaultClientScopes", [])
        if name not in scopes:
            scopes.append(name)
            self.update_client(client_id, {"defaultClientScopes": scopes})
        return {}

    def get_client_role(self, client_id: str, role_name: str) -> dict:
        self.calls.append(("get_client_role", client_id, role_name))
        return {"id": f"role-{role_name}", "name": role_name}

    def get_client_roles_of_user(self, user_id: str, client_id: str) -> list:
        self.calls.append(("get_client_roles_of_user", user_id, client_id))
        service_account_client_id = user_id.removeprefix("service-account-")
        names = self.service_account_roles.get(service_account_client_id, {}).get(
            "realm-management", set()
        )
        return [{"name": name} for name in names]

    def assign_client_role(self, user_id: str, client_id: str, roles) -> dict:
        self.calls.append(("assign_client_role", user_id, client_id, roles))
        service_account_client_id = user_id.removeprefix("service-account-")
        mapping = self.service_account_roles.setdefault(service_account_client_id, {})
        names = mapping.setdefault("realm-management", set())
        for role in roles:
            names.add(role["name"])
        return {}

    def get_client_roles_of_client_scope(
        self, client_id: str, client_roles_owner_id: str
    ) -> list:
        self.calls.append(
            ("get_client_roles_of_client_scope", client_id, client_roles_owner_id)
        )
        names = self.client_scope_roles.get((client_id, client_roles_owner_id), set())
        return [{"name": name} for name in names]

    def assign_client_roles_to_client_scope(
        self, client_id: str, client_roles_owner_id: str, roles
    ) -> dict:
        self.calls.append(
            (
                "assign_client_roles_to_client_scope",
                client_id,
                client_roles_owner_id,
                roles,
            )
        )
        names = self.client_scope_roles.setdefault(
            (client_id, client_roles_owner_id), set()
        )
        for role in roles:
            names.add(role["name"])
        return {}

    def calls_of(self, name: str) -> list:
        return [call for call in self.calls if call[0] == name]

    def _group_by_id(self, group_id: str) -> dict:
        for group in self.groups:
            if group["id"] == group_id:
                return group
        raise KeycloakGetError("group not found", response_code=404)
