from django.conf import settings
from django.db import migrations
from django.utils import timezone


def copy_fields(source, target_model, excluded_field_names: set[str]) -> dict:
    target_field_names = {field.name for field in target_model._meta.concrete_fields}
    return {
        field.name: getattr(source, field.name)
        for field in source._meta.concrete_fields
        if field.name in target_field_names and field.name not in excluded_field_names
    }


def copy_to_jasmin_tenant(apps, schema_editor):
    """Jasmin's own Tenant and TenantSettings replace Tapir's copies of them."""
    Tenant = apps.get_model("tenants", "Tenant")
    TenantSettings = apps.get_model("tenants", "TenantSettings")
    JasminTenant = apps.get_model("jasmin_integration", "JasminTenant")
    JasminTenantSettings = apps.get_model("jasmin_integration", "JasminTenantSettings")

    if Tenant.objects.filter(schema_name=settings.JASMIN_TENANT_SCHEMA_NAME).exists():
        return

    jasmin_tenant = JasminTenant.objects.first()
    tenant = Tenant.objects.create(
        **(
            copy_fields(jasmin_tenant, Tenant, {"id", "schema_name"})
            if jasmin_tenant is not None
            else {"name": "Tapir", "tenant_language": "de"}
        ),
        schema_name=settings.JASMIN_TENANT_SCHEMA_NAME,
    )

    jasmin_tenant_settings = list(JasminTenantSettings.objects.order_by("valid_from"))
    if len(jasmin_tenant_settings) == 0:
        TenantSettings.objects.create(
            tenant=tenant,
            valid_from=timezone.now(),
            uploads_weekly_share_amount=True,
        )
        return

    for jasmin_tenant_setting in jasmin_tenant_settings:
        TenantSettings.objects.create(
            tenant=tenant,
            **copy_fields(jasmin_tenant_setting, TenantSettings, {"id", "tenant"}),
        )


class Migration(migrations.Migration):
    dependencies = [
        ("jasmin_integration", "0003_jasmintenantsettings"),
        ("tenants", "0021_tenantsettings_info_sentence_about_coop_shares"),
    ]

    operations = [
        migrations.RunPython(copy_to_jasmin_tenant, migrations.RunPython.noop),
    ]
