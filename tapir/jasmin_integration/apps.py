from django.apps import AppConfig, apps


class JasminIntegrationConfig(AppConfig):
    name = "tapir.jasmin_integration"

    def ready(self):
        if not apps.is_installed("apps.shared.tenants"):
            return

        from apps.shared.tenants.models import Tenant

        # Tapir's tables all live in the public schema, see
        # tapir.jasmin_integration.db_backend: django-tenants must not create a
        # schema when a tenant is saved (it would run its migrate_schemas command,
        # which isn't installed) nor drop one when a tenant is deleted.
        Tenant.auto_create_schema = False
        Tenant.auto_drop_schema = False
