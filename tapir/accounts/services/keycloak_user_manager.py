from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from keycloak import KeycloakAdmin

from tapir.accounts.services.keycloak_client_factory import get_runtime_client
from tapir.accounts.services.keycloak_username_service import (
    KeycloakUsernameService,
)

if TYPE_CHECKING:
    from tapir.accounts.models import KeycloakUser


class KeycloakUserManager:
    @classmethod
    def create_keycloak_user_if_necessary(
        cls,
        user: KeycloakUser,
        initial_password: str | None,
    ):
        if user.keycloak_id:
            cls.update_keycloak_user_attributes(user)
            return

        username = KeycloakUsernameService.build_username(user)
        data: dict = {
            "username": username,
            "email": user.email,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "enabled": True,
        }

        if initial_password:
            data["credentials"] = [{"value": initial_password, "type": "password"}]
            data["emailVerified"] = True
        else:
            data["requiredActions"] = ["VERIFY_EMAIL", "UPDATE_PASSWORD"]

        if user.is_superuser:
            data["groups"] = [settings.KEYCLOAK_SUPERUSER_GROUP_NAME]
        else:
            data["groups"] = []

        attributes = cls._user_profile_attributes(user)
        if attributes:
            data["attributes"] = attributes

        keycloak_client = KeycloakUserManager.get_keycloak_client()
        user.keycloak_id = keycloak_client.create_user(data)

        SocialAccount.objects.create(
            user=user, provider="keycloak", uid=user.keycloak_id
        )

        user.save()

    @classmethod
    def update_keycloak_user_name(cls, user: KeycloakUser):
        data = {"firstName": user.first_name, "lastName": user.last_name}
        keycloak_client = cls.get_keycloak_client()
        keycloak_client.update_user(user_id=user.keycloak_id, payload=data)

    @classmethod
    def update_keycloak_user_attributes(cls, user: KeycloakUser):
        mapping = settings.KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP
        if not user.keycloak_id or not mapping:
            return

        attributes = cls._user_profile_attributes(user)
        keycloak_client = cls.get_keycloak_client()
        current = keycloak_client.get_user(user.keycloak_id) or {}
        current_attributes = dict(current.get("attributes") or {})
        merged = dict(current_attributes)
        for entry in mapping:
            attribute_name = entry["keycloak"]
            if attribute_name in attributes:
                merged[attribute_name] = attributes[attribute_name]
            else:
                merged.pop(attribute_name, None)

        if merged == current_attributes:
            return

        payload = {
            key: current[key]
            for key in (
                "username",
                "email",
                "firstName",
                "lastName",
                "enabled",
                "emailVerified",
                "requiredActions",
            )
            if key in current
        }
        payload["attributes"] = merged
        keycloak_client.update_user(user_id=user.keycloak_id, payload=payload)

    @classmethod
    def _user_profile_attributes(cls, user: KeycloakUser) -> dict[str, list[str]]:
        attributes: dict[str, list[str]] = {}
        for entry in settings.KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP:
            value = getattr(user, entry["tapir"], None)
            if value is None or value == "":
                continue
            attributes[entry["keycloak"]] = [str(value)]
        return attributes

    @classmethod
    def find_keycloak_user_by_email(cls, email: str) -> dict | None:
        keycloak_client = cls.get_keycloak_client()
        users = keycloak_client.get_users(query={"email": email, "exact": True})
        return users[0] if users else None

    @classmethod
    @functools.cache
    def get_keycloak_client(cls) -> KeycloakAdmin:
        return get_runtime_client()

    @classmethod
    def get_user_roles(cls, keycloak_id):
        keycloak_client = KeycloakUserManager.get_keycloak_client()

        raw_roles = keycloak_client.get_composite_realm_roles_of_user(
            keycloak_id,
        )

        realm_name = settings.KEYCLOAK_ADMIN_CONFIG["REALM_NAME"]
        non_tapir_roles = {
            *settings.KEYCLOAK_NON_TAPIR_ROLES,
            "offline_access",
            "uma_authorization",
            f"default-roles-{realm_name}",
        }
        return [
            raw_role["name"]
            for raw_role in raw_roles
            if raw_role["name"] not in non_tapir_roles
        ]
