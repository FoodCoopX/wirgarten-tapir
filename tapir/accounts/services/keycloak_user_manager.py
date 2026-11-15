from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from keycloak import KeycloakAdmin

from tapir.accounts.services.keycloak_client_factory import get_runtime_client

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
            return

        data: dict = {
            "username": user.email,
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
            data["groups"] = ["superuser"]
        else:
            data["groups"] = []

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
