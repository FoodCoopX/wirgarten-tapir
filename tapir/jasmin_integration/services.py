from tapir.jasmin_integration.models import JasminTenantSettings
from tapir.wirgarten.utils import get_now


def get_current_jasmin_tenant_settings(
    cache: dict | None = None,
) -> JasminTenantSettings:
    settings, _ = JasminTenantSettings.objects.get_or_create(
        defaults={
            "uploads_weekly_share_amount": True,
            "valid_from": get_now(cache=cache),
        }
    )
    return settings
