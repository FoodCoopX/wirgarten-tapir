from django.conf import settings
from django.db.backends.postgresql import base
from django_tenants.postgresql_backend.base import FakeTenant
from django_tenants.utils import get_public_schema_name, get_tenant_model


class DatabaseWrapper(base.DatabaseWrapper):
    """Django's PostgreSQL backend, plus the tenant API that django-tenants' backend
    adds to the connection: ``tenant``, ``schema_name``, ``set_tenant``,
    ``set_schema`` and ``set_schema_to_public``.

    Jasmin reads and switches the active tenant through that API. Tapir is a single
    tenant whose tables all live in the public schema, so switching only changes
    which tenant Jasmin sees: unlike with django-tenants, the search path is never
    changed. Until something switches it, the active tenant is Tapir's own tenant,
    the one whose schema name is ``settings.JASMIN_TENANT_SCHEMA_NAME``."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tenant = None

    @property
    def tenant(self):
        if self._tenant is None:
            default_tenant = self.get_default_tenant()
            if default_tenant is None:
                # Not created yet (for example before the migrations ran): like
                # django-tenants, the connection starts in the public schema.
                return FakeTenant(schema_name=get_public_schema_name())
            self._tenant = default_tenant
        return self._tenant

    @property
    def schema_name(self) -> str:
        return self.tenant.schema_name

    def set_tenant(self, tenant, include_public=True):
        self._tenant = tenant

    def set_schema(self, schema_name, include_public=True, tenant_type=None):
        self._tenant = FakeTenant(schema_name=schema_name, tenant_type=tenant_type)

    def set_schema_to_public(self):
        self.set_schema(get_public_schema_name())

    def reset_tenant(self):
        """Back to Tapir's tenant. Connections are reused across requests: a tenant
        switched during one request must not stay active in the next."""
        self._tenant = None

    def get_default_tenant(self):
        tenant_model = get_tenant_model()
        if tenant_model._meta.db_table not in self.introspection.table_names():
            return None
        return tenant_model.objects.filter(
            schema_name=settings.JASMIN_TENANT_SCHEMA_NAME
        ).first()
