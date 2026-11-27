from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from tapir.accounts.models import KeycloakUser


class KeycloakUsernameUnavailable(Exception):
    pass


class KeycloakUsernameService:
    @classmethod
    def can_create_keycloak_user(cls, user: KeycloakUser) -> bool:
        if settings.KEYCLOAK_USERNAME_SOURCE == "email":
            return True
        if not hasattr(user, "member_no"):
            return True
        return user.member_no is not None

    @classmethod
    def uses_email_username(cls, user: KeycloakUser) -> bool:
        if settings.KEYCLOAK_USERNAME_SOURCE == "email":
            return True
        if not hasattr(user, "member_no"):
            return True
        return user.member_no is None

    @classmethod
    def build_username(cls, user: KeycloakUser) -> str:
        if settings.KEYCLOAK_USERNAME_SOURCE == "email":
            return user.email
        if not hasattr(user, "member_no"):
            return user.email
        if user.member_no is None:
            raise KeycloakUsernameUnavailable(
                "The member has no member number yet; the Keycloak user is created "
                "after a member number is assigned. Assign a member number first or "
                "use KEYCLOAK_USERNAME_SOURCE=email."
            )
        return cls._member_number_value(user)

    @classmethod
    def _member_number_value(cls, user: KeycloakUser) -> str:
        if settings.KEYCLOAK_USERNAME_FORMAT == "raw":
            return str(user.member_no)
        from tapir.coop.services.member_number_service import MemberNumberService

        return MemberNumberService.format_member_number(user.member_no, cache={})
