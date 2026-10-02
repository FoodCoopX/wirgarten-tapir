import logging

from django.conf import settings

from tapir.accounts.models import KeycloakUser, TapirUser
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.log.models import TextLogEntry

LOG = logging.getLogger(__name__)


class EmailVerificationService:
    @classmethod
    def is_user_email_verified(cls, user: KeycloakUser, cache: dict) -> bool:
        kc = KeycloakUserManager.get_keycloak_client(cache=cache)
        try:
            kc_user = kc.get_user(user.keycloak_id)
            return kc_user["emailVerified"]
        except Exception:
            return False

    @classmethod
    def send_verification_email(
        cls, user: KeycloakUser, actor: TapirUser | None, cache: dict
    ):
        if settings.KEYCLOAK_SKIP_VERIFICATION_EMAIL:
            print(f"Skipping email verification for {user.email}")
        else:
            kc = KeycloakUserManager.get_keycloak_client(cache=cache)
            kc.send_verify_email(
                user_id=user.keycloak_id,
                redirect_uri=settings.SITE_URL,
                client_id=settings.KEYCLOAK_ADMIN_CONFIG["FRONTEND_CLIENT_ID"],
            )

        TextLogEntry().populate(
            text='Keycloak Email gesendet: "Aktivierung des Benutzerkontos"',
            user=user,
            actor=actor,
        ).save()
