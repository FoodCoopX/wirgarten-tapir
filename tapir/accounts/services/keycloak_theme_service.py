from django.conf import settings

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.utils.config import Organization

KEYCLOAK_THEME_WIRGARTEN = "wirgarten"
KEYCLOAK_THEME_VIERLANDE = "vie"

REALM_DISPLAY_NAME_DEFAULT = "Tapir Test"
REALM_DISPLAY_NAME_SOLAWI_VIERLANDE = "Solawi Vierlande e.V."
REALM_DISPLAY_NAME_HTML_SOLAWI_VIERLANDE = "🥕 Solawi Vierlande e.V. 🥕"


class KeycloakThemeService:
    @classmethod
    def set_realm_configuration_for_organization(cls, organization, cache: dict):
        keycloak_client = KeycloakUserManager.get_keycloak_client()
        keycloak_client.update_realm(
            realm_name=settings.KEYCLOAK_ADMIN_CONFIG["REALM_NAME"],
            payload=cls.get_realm_configuration_for_organization(organization),
        )

    @classmethod
    def get_realm_configuration_for_organization(cls, organization) -> dict:
        if organization == Organization.VIERLANDE:
            theme = KEYCLOAK_THEME_VIERLANDE
            return {
                "loginTheme": theme,
                "emailTheme": theme,
                "accountTheme": theme,
                "adminTheme": theme,
                "displayName": REALM_DISPLAY_NAME_SOLAWI_VIERLANDE,
                "displayNameHtml": REALM_DISPLAY_NAME_HTML_SOLAWI_VIERLANDE,
                "registrationEmailAsUsername": False,
            }

        theme = KEYCLOAK_THEME_WIRGARTEN
        return {
            "loginTheme": theme,
            "emailTheme": theme,
            "accountTheme": "",
            "adminTheme": "",
            "displayName": REALM_DISPLAY_NAME_DEFAULT,
            "displayNameHtml": "",
            "registrationEmailAsUsername": True,
        }
