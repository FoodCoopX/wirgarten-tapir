from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction
from keycloak import KeycloakOpenIDConnection, KeycloakAdmin

from tapir.utils.shortcuts import get_from_cache_or_compute

if TYPE_CHECKING:
    from tapir.accounts.models import KeycloakUser


class KeycloakUserManager:
    @classmethod
    def create_keycloak_user(
        cls,
        user: KeycloakUser,
        keycloak_client: KeycloakAdmin,
        initial_password: str | None,
        cache: dict,
    ):
        data: dict = {
            "username": user.email,
            "email": user.email,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "enabled": True,
        }

        keycloak_id = keycloak_client.get_user_id(user.email)
        if keycloak_id is not None:
            user.keycloak_id = keycloak_id
            keycloak_client.update_user(user_id=user.keycloak_id, payload=data)
            return

        if initial_password:
            data["credentials"] = [{"value": initial_password, "type": "password"}]
            data["emailVerified"] = True
        else:
            data["requiredActions"] = ["VERIFY_EMAIL", "UPDATE_PASSWORD"]

        if user.is_superuser:
            group = keycloak_client.get_group_by_path(path="/superuser")
            if group:
                data["groups"] = ["superuser"]

        user.keycloak_id = keycloak_client.create_user(data)

        if user.email.endswith("@example.com"):
            return

        try:
            transaction.on_commit(partial(user.send_verify_email, cache=cache))
        except Exception as e:
            print(
                f"Failed to send verify email to new user: ",
                e,
                f" (email: '{user.email}', id: '{user.id}', keycloak_id: '{user.keycloak_id}'): ",
            )

    @classmethod
    def update_keycloak_user(
        cls,
        user: KeycloakUser,
        keycloak_client: KeycloakAdmin,
        old_first_name: str,
        old_last_name: str,
        old_email: str,
        new_first_name: str,
        new_last_name: str,
        new_email: str,
        cache: dict,
    ):
        if old_first_name != new_first_name or old_last_name != new_last_name:
            data = {"firstName": user.first_name, "lastName": user.last_name}
            keycloak_client.update_user(user_id=user.keycloak_id, payload=data)

        if old_email == new_email:
            return

        if user.email_verified(cache=cache):
            from tapir.accounts.services.mail_change_service import (
                MailChangeService,
            )

            MailChangeService.start_email_change_process(
                user=user, new_email=new_email, orig_email=old_email
            )
            return

        # in this case, don't start the email change process, just send the keycloak email to the new address and resend the link
        keycloak_client.update_user(
            user_id=user.keycloak_id, payload={"email": new_email}
        )
        user.send_verify_email()

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
