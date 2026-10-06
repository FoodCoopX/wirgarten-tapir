from __future__ import annotations

from typing import TYPE_CHECKING

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from keycloak import KeycloakOpenIDConnection, KeycloakAdmin

from tapir.utils.shortcuts import get_from_cache_or_compute

if TYPE_CHECKING:
    from tapir.accounts.models import KeycloakUser


class KeycloakUserManager:
    @classmethod
    def create_keycloak_user_if_necessary(
        cls,
        user: KeycloakUser,
        initial_password: str | None,
        cache: dict,
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

        keycloak_client = KeycloakUserManager.get_keycloak_client(cache)
        user.keycloak_id = keycloak_client.create_user(data)

        SocialAccount.objects.create(
            user=user, provider="keycloak", uid=user.keycloak_id
        )

        user.save()

    @classmethod
    def update_keycloak_user_name(cls, user: KeycloakUser, cache: dict):
        data = {"firstName": user.first_name, "lastName": user.last_name}
        keycloak_client = cls.get_keycloak_client(cache)
        keycloak_client.update_user(user_id=user.keycloak_id, payload=data)

    @classmethod
    def get_keycloak_client(cls, cache: dict):
        def compute():
            config = settings.KEYCLOAK_ADMIN_CONFIG

            keycloak_connection = KeycloakOpenIDConnection(
                server_url=config["SERVER_URL"],
                realm_name=config["REALM_NAME"],
                client_id=config["CLIENT_ID"],
                client_secret_key=config["CLIENT_SECRET_KEY"],
                verify=True,
            )

            return KeycloakAdmin(connection=keycloak_connection)

        return get_from_cache_or_compute(
            cache=cache, key="keycloak_client", compute_function=compute
        )

    @classmethod
    def get_user_roles(cls, keycloak_id):
        keycloak_client = KeycloakUserManager.get_keycloak_client(cache={})

        raw_roles = keycloak_client.get_composite_realm_roles_of_user(
            keycloak_id,
        )

        return [
            raw_role["name"]
            for raw_role in raw_roles
            if raw_role["name"] not in settings.KEYCLOAK_NON_TAPIR_ROLES
        ]
