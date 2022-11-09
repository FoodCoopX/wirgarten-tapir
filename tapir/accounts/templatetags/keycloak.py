import json

from django import template

from tapir import settings

register = template.Library()


@register.simple_tag
def keycloak_config() -> str:
    return json.dumps(
        {
            "url": settings.KEYCLOAK_ADMIN_CONFIG["PUBLIC_URL"],
            "realm": settings.KEYCLOAK_ADMIN_CONFIG["USER_REALM_NAME"],
            "clientId": settings.KEYCLOAK_ADMIN_CONFIG["FRONTEND_CLIENT_ID"],
            "publicClient": True,
        }
    )


@register.simple_tag
def keycloak_public_url() -> str:
    return settings.KEYCLOAK_ADMIN_CONFIG["PUBLIC_URL"]
